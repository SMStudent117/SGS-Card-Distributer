% 批量降低 PNG 图片分辨率并保存到 images_low 文件夹
clc; clear;

% 设置路径
inputFolder  = fullfile(pwd, 'images');      % 原图文件夹
outputFolder = fullfile(pwd, 'images_low');  % 输出文件夹

% 如果输出文件夹不存在则创建
if ~exist(outputFolder, 'dir')
    mkdir(outputFolder);
end

% 获取所有 PNG 文件
fileList = dir(fullfile(inputFolder, '*.png'));

% 缩放比例 (例如 0.5 表示缩小一半)
scale = 0.5;

for i = 1:length(fileList)
    % 构造完整路径
    inputPath  = fullfile(inputFolder, fileList(i).name);
    outputPath = fullfile(outputFolder, fileList(i).name);

    % 如果输出文件已存在，跳过
    if exist(outputPath, 'file')
        fprintf('已存在，跳过: %s\n', fileList(i).name);
        continue;
    end

    % 读取图片
    img = imread(inputPath);

    % 调整大小
    img_resized = imresize(img, scale);

    % 保存到目标文件夹
    imwrite(img_resized, outputPath);

    fprintf('已处理: %s\n', fileList(i).name);
end

disp('所有图片已处理完成！');
