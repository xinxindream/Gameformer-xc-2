import random
import shutil
import os


# if __name__ == "__main__":
#     source_folder = '/media/xingchen24/xingchen/datasets/nuplan/datasets/nuplan/train_processed_data_0.35M-/train'
#     destination_folder = '/media/xingchen24/xingchen/datasets/nuplan/datasets/nuplan/train'
#
#     # 遍历源文件夹中的所有文件并复制
#     filenames = os.listdir(source_folder)
#     val_ratio = 0.08
#     print(f"Total number of frames: {len(filenames)}")
#     val_num = int(len(filenames) * val_ratio)
#     selected_val_filenames = random.sample(filenames, val_num)
#     selected_train_filenames = list(set(filenames) - set(selected_val_filenames))
#     for filename in selected_val_filenames:
#         source_file = os.path.join(source_folder, filename)
#         destination_file = os.path.join(destination_folder, filename)
#
#         # 确保是文件而不是文件夹
#         if os.path.isfile(source_file):
#             shutil.move(source_file, destination_file)

# if __name__ == "__main__":
#     source_folder = '/media/xingchen24/xingchen/datasets/learn_based_planner/xiaoba/train-1221-likenuplan/data/2023.12.21'
#     destination_train_folder = '/media/xingchen24/xingchen/datasets/learn_based_planner/xiaoba/train-1221-likenuplan/train-1221'
#     destination_val_folder = '/media/xingchen24/xingchen/datasets/learn_based_planner/xiaoba/train-1221-likenuplan/val-1221'
#
#     os.makedirs(destination_train_folder, exist_ok=True)
#     os.makedirs(destination_val_folder, exist_ok=True)
#
#     selected_files_npy = []
#     val_ratio = 0.1
#     filenames = os.listdir(source_folder)
#     for filename in filenames:
#         if os.path.isfile(os.path.join(source_folder, filename)): continue
#         sub_filenames = os.listdir(os.path.join(source_folder, filename))
#         for sub_filename in sub_filenames:
#             if sub_filename.endswith('.npz'):
#                 selected_files_npy.append(os.path.join(source_folder, filename, sub_filename))
#     print(f"Total number of frames: {len(selected_files_npy)}")
#     val_num = int(len(selected_files_npy) * val_ratio)
#     selected_val_filenames = random.sample(selected_files_npy, val_num)
#     selected_train_filenames = list(set(selected_files_npy) - set(selected_val_filenames))
#     for filename in selected_train_filenames:
#         source_file = filename
#         destination_file = os.path.join(destination_train_folder, os.path.basename(source_file))
#         shutil.copy(source_file, destination_file)
#     print('train completed')
#     for filename in selected_val_filenames:
#         source_file = filename
#         destination_file = os.path.join(destination_val_folder, os.path.basename(source_file))
#         shutil.copy(source_file, destination_file)
#     print('val completed')

if __name__ == "__main__":
    data_path = '/data/datasets/xiaoba/2024.1.11/2024-01-11-17-20-37_part1_with_det_2_train/'
    train_set_path = data_path + 'train/'
    valid_set_path = data_path + 'valid/'

    os.makedirs(train_set_path, exist_ok=True)
    os.makedirs(valid_set_path, exist_ok=True)

    data = []
    filenames = os.listdir(data_path)
    for filename in filenames:
        if filename.endswith('.npz'):
            data.append(os.path.join(data_path, filename))

    num_train_set = int(len(data) * 0.9)

    random.shuffle(data)
    for i in range(num_train_set):
        shutil.move(data[i], train_set_path)

    for j in range(num_train_set, len(data)):
        shutil.move(data[j], valid_set_path)