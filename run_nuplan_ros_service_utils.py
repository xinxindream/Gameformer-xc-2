import math
#
# import rospy
# from geometry_msgs.msg import Pose, Vector3
# from nav_msgs.msg import Path
#
# from kxdun_perception_msgs.msg import PerceptionObstacle, PerceptionObstacleArray, PerceptionLaneArray, PerceptionLane
# from kxdun_localization_msgs.msg import Localization

import torch

def get_tracked_objects_to_tensor_list(agents_past_queue):
    # 创建一个空字典，用于保存每个物体的信息
    objects_list = []
    objects_type_list = []

    print('agents_past.vehicle_set.vehicles',len(agents_past_queue[0].vehicle_set.vehicles)-1)
    for agents_past in agents_past_queue:
        # 创建一个物体数量 * 8 的张量
        obj_tensor = torch.zeros((len(agents_past.vehicle_set.vehicles) - 1, 8), dtype=torch.float32)
        objects_type = []
        for i, past_tracked_object in enumerate(agents_past.vehicle_set.vehicles):
            if i == 0:
                continue
            i = i - 1
            obj_tensor[i, 0] = float(past_tracked_object.id.data)
            if past_tracked_object.state.velocity > 0.5:
                obj_tensor[i, 1] = past_tracked_object.state.velocity*math.sin(past_tracked_object.state.angle)
                obj_tensor[i, 2] = past_tracked_object.state.velocity*math.cos(past_tracked_object.state.angle)
                obj_tensor[i, 3] = past_tracked_object.state.angle
            else:
                obj_tensor[i, 1] = past_tracked_object.state.velocity * math.sin(past_tracked_object.state.angle) #可能考虑直接为0
                obj_tensor[i, 2] = past_tracked_object.state.velocity * math.cos(past_tracked_object.state.angle)
                obj_tensor[i, 3] = past_tracked_object.state.angle
            obj_tensor[i, 4] = past_tracked_object.param.width
            obj_tensor[i, 5] = past_tracked_object.param.length
            obj_tensor[i, 6] = past_tracked_object.state.vec_position.x
            obj_tensor[i, 7] = past_tracked_object.state.vec_position.y
            # print('2222')
            if past_tracked_object.subclass.data == 'car':
                # print('objects_type.append(TrackedObjectType.VEHICLE)')
                objects_type.append(TrackedObjectType.VEHICLE)
            elif past_tracked_object.subclass.data == 'person':
                objects_type.append(TrackedObjectType.PEDESTRIAN)
            elif past_tracked_object.subclass.data == 'bicycle':
                objects_type.append(TrackedObjectType.BICYCLE)
            elif past_tracked_object.subclass.data == 'cone':
                objects_type.append(TrackedObjectType.TRAFFIC_CONE)
            elif past_tracked_object.subclass.data == 'barrier':
                objects_type.append(TrackedObjectType.BARRIER)
            elif past_tracked_object.subclass.data == 'czone_sign':
                objects_type.append(TrackedObjectType.CZONE_SIGN)
            elif past_tracked_object.subclass.data == 'generic_object':
                objects_type.append(TrackedObjectType.GENERIC_OBJECT)
            elif past_tracked_object.subclass.data == 'ego':
                objects_type.append(TrackedObjectType.EGO)

        # 按照 id 的大小对张量的行进行排序
        first_column = obj_tensor[:, 0]
        sorted_indices = torch.argsort(first_column)
        sorted_obj_tensor = obj_tensor[sorted_indices]
        objects_list.append(sorted_obj_tensor)
        objects_type_list.append(objects_type)
    return objects_list, objects_type_list

def get_ego_past_to_tensor_list(ego_past_queue):

    ego_tensor = torch.zeros((len(ego_past_queue), 7), dtype=torch.float32)
    for i, ego_past in enumerate(ego_past_queue):
        ego_tensor[i, 0] = ego_past.vehicle_set.vehicles[0].state.vec_position.x
        ego_tensor[i, 1] = ego_past.vehicle_set.vehicles[0].state.vec_position.y
        ego_tensor[i, 2] = ego_past.vehicle_set.vehicles[0].state.angle
        ego_tensor[i, 3] = ego_past.vehicle_set.vehicles[0].state.velocity * math.sin(ego_past.vehicle_set.vehicles[0].state.angle)
        ego_tensor[i, 4] = ego_past.vehicle_set.vehicles[0].state.velocity * math.cos(ego_past.vehicle_set.vehicles[0].state.angle)
        ego_tensor[i, 5] = ego_past.vehicle_set.vehicles[0].state.acceleration * math.sin(ego_past.vehicle_set.vehicles[0].state.angle)
        ego_tensor[i, 6] = ego_past.vehicle_set.vehicles[0].state.acceleration * math.cos(ego_past.vehicle_set.vehicles[0].state.angle)
    return ego_tensor


def get_past_timestamps_to_tensor(_ego_past_queue):
    flat = [ego_past.header.stamp.to_sec() * 1e6 for ego_past in _ego_past_queue]
    # print(torch.tensor(flat, dtype=torch.int64))
    # print(flat)
    return torch.tensor(flat, dtype=torch.int64)

def get_map_lane_polylines(_map_lane_array):
    lanes_mid: List[List[Point2D]] = []

    for one_map_lane in _map_lane_array.lane_net.lanes:
        baseline_path_polyline = [Point2D(node.x, node.y) for node in one_map_lane.points]
        lanes_mid.append(baseline_path_polyline)
        # print('one_map_lane')

    return MapObjectPolylines(lanes_mid)

def get_route_lane_polylines(_route_lane_array):
    route_lane_polylines: List[List[Point2D]] = []

    for one_route_lane in _route_lane_array.lane_net.lanes:
        baseline_path_polyline = [Point2D(node.x, node.y) for node in one_route_lane.points]
        route_lane_polylines.append(baseline_path_polyline)

    return MapObjectPolylines(route_lane_polylines)

def convert_to_model_inputs(data, device):
    tensor_data = {}
    for k, v in data.items():
        tensor_data[k] = v.float().unsqueeze(0).to(device)

    return tensor_data

from typing import Any, Callable, Dict, List, Optional, Set, Tuple, cast
import numpy as np
import struct
import torch
from Planner.observation import *
from Planner.planner_utils import *
from nuplan.planning.training.preprocessing.utils.agents_preprocessing import *
from nuplan.common.actor_state.tracked_objects_types import TrackedObjectType
from nuplan.planning.training.preprocessing.feature_builders.vector_builder_utils import *

num_agents = 20
map_features = ['LANE', 'ROUTE_LANES', 'CROSSWALK'] # name of map features to be extracted.
max_elements = {'LANE': 40, 'ROUTE_LANES': 10, 'CROSSWALK': 5} # maximum number of elements to extract per feature layer.
max_points = {'LANE': 50, 'ROUTE_LANES': 50, 'CROSSWALK': 30} # maximum number of points per feature to extract per feature layer.
radius = 60 # [m] query radius scope relative to the current pose.
interpolation_method = 'linear'

lanes_mid: List[List[Point2D]] = []
baseline_path_polyline = [Point2D(i *10, i*20) for i in range(22)]
lanes_mid.append(baseline_path_polyline)
lanes_mid.append(baseline_path_polyline)
coords_map_lanes_polylines = MapObjectPolylines(lanes_mid)
route_lane_polylines: List[List[Point2D]] = []
baseline_path_polyline = [Point2D(i *10, i*20) for i in range(22)]
route_lane_polylines.append(baseline_path_polyline)
coords_route_lanes_polylines = MapObjectPolylines(route_lane_polylines)
crosswalk: List[List[Point2D]] = []
coords_crosswalk_polylines = MapObjectPolylines(crosswalk)
coords: Dict[str, MapObjectPolylines] = {}
coords[map_features[0]] = coords_map_lanes_polylines
coords[map_features[1]] = coords_route_lanes_polylines
coords[map_features[2]] = coords_crosswalk_polylines

traffic_light_encoding = np.zeros([len(lanes_mid), 4], dtype=int)
traffic_light_encoding[:,-1] = 1
traffic_light_data_at_t: Dict[str, LaneSegmentTrafficLightData] = {}
traffic_light_data: List[Dict[str, LaneSegmentTrafficLightData]] = []
traffic_light_data_at_t[map_features[0]] = LaneSegmentTrafficLightData(list(map(tuple, traffic_light_encoding)))
# traffic_light_data.append(traffic_light_data_at_t)

# traffic_light_encoding = np.zeros([len(route_lane_polylines),4], dtype=int)
# traffic_light_encoding[:,-1] = 1
# traffic_light_data: Dict[str, LaneSegmentTrafficLightData] = {}
# traffic_light_data[map_features[0]] = LaneSegmentTrafficLightData(list(map(tuple, traffic_light_encoding)))
ego_state = StateSE2(x=20, y=40,heading=0)
vector_map = map_process(ego_state, coords, traffic_light_data_at_t, map_features, max_elements, max_points, interpolation_method)


# class PerceptionObstacle:
#     def __init__(self, id, x, y):
#         self.id = id
#         self.x = x
#         self.y = y
# ## 测试ego和neighbor的处理 ##
# _agents_past_queue = []
# _agents_past_id_queue = []
# for i in range(22):
#     obstacle_list = torch.tensor([[0, 0, 0, 0, 0, 0, 0, 0]])
#     obstacle_id_list = [TrackedObjectType.VEHICLE]
#     for j in range(i):
#         added_obstacle = torch.tensor([[j, j*10 + i, j*20 + i, j, 0, 0, 0, 0]])
#         added_obstacle_id = TrackedObjectType.VEHICLE
#         obstacle_list = torch.cat([obstacle_list, added_obstacle], dim=0)
#         obstacle_id_list.append(added_obstacle_id)
#     _agents_past_queue.append(obstacle_list)
#     _agents_past_id_queue.append(obstacle_id_list)
#
# ego_agent_past = torch.tensor([[j, j*10 + i, j*20 + i, j, 0, 0, 0]])
# for j in range(21):
#     ego_ = torch.tensor([[j, j*10 + i, j*20 + i, j, 0, 0, 0]])
#     ego_agent_past = torch.cat([ego_agent_past, ego_], dim=0)
#
# time_stamps_past = ([i*0.1*1000000 for i in range(22)])
# flat = [t for t in time_stamps_past]
# time_stamps_past = torch.tensor(flat, dtype=torch.int64)
# # agent_history = filter_agents_tensor(_agents_past_queue, reverse=True)
#
# ego_agent_past, neighbor_agents_past = agent_past_process(
#         ego_agent_past, time_stamps_past, _agents_past_queue, _agents_past_id_queue, 20
#     )
#
# # 假设你有一个包含 20 帧物体信息的队列 objects_queue
# objects_queue = [
#     [{'id': 1, 'x': 0, 'y': 0}, {'id': 2, 'x': 1, 'y': 1}],
#     [{'id': 1, 'x': 0.1, 'y': 0.1}, {'id': 3, 'x': 1.1, 'y': 1.1}, {'id': 4, 'x': 2.1, 'y': 2.1}],
#     [{'id': 1, 'x': 0.2, 'y': 0.2}, {'id': 2, 'x': 1.2, 'y': 1.2}, {'id': 3, 'x': 2.2, 'y': 2.2}, {'id': 4, 'x': 3.2, 'y': 3.2}],
#     # ...
#     [{'id': 1, 'x': 1.9, 'y': 1.9}, {'id': 2, 'x': 2.9, 'y': 2.9}]
# ]
#
# # 创建一个空字典，用于保存每个物体的信息
# objects_dict = {}
#
# # 遍历每个帧中的物体信息
# for frame in objects_queue:
#     # 遍历每个物体
#     for obj in frame:
#         obj_id = obj['id']
#         # 如果物体在字典中不存在，将其添加到字典中
#         if obj_id not in objects_dict:
#             objects_dict[obj_id] = {'x': 0, 'y': 0}
#         # 更新物体的位置
#         objects_dict[obj_id]['x'] = obj['x']
#         objects_dict[obj_id]['y'] = obj['y']
#     # 创建一个物体数量 * 3 的张量
#     tensor = np.zeros((len(objects_dict), 3))
#     # 将物体信息按照 id 顺序添加到张量中
#     for i, obj_id in enumerate(sorted(objects_dict.keys())):
#         tensor[i, 0] = obj_id
#         tensor[i, 1] = objects_dict[obj_id]['x']
#         tensor[i, 2] = objects_dict[obj_id]['y']
#     # 打印结果
#     print(tensor)
