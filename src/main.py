import click
import json
from pathlib import Path

from torch import cuda, nn, optim
from torch.utils.data import DataLoader
from tensorboardX import SummaryWriter
from train_val import train, val
from datasets.dataset import CustomDataset
from models.model import CustomResnet18

def get_data_loaders(path_to_data, batch_size=1, workers_num=1):
    if path_to_data['train_img'] is not None and path_to_data['train_annot'] is not None:
        train_data_loaders = DataLoader(CustomDataset(path_to_data['train_img'], path_to_data['train_annot']), batch_size,
                                        num_workers=workers_num)
    else:
        train_data_loaders = None
    if path_to_data['val_img'] is not None and path_to_data['val_annot'] is not None:
        val_data_loaders = DataLoader(CustomDataset(path_to_data['val_img'], path_to_data['val_annot']), batch_size,
                                        num_workers=workers_num)

    else:
        val_data_loaders = None
    return {'train': train_data_loaders, 'val':val_data_loaders}


def load_json(path_to_json):
    with path_to_json.open() as json_file:
        configs = json.load(json_file)
    return configs


@click.command()
@click.option('--config-path', required=True, help='the path to config.json', type=str)
def main(config_path):
    path_to_config = Path(config_path)

    if not (path_to_config.exists()):
        raise ValueError('{} doesn\'t exist'.format(path_to_config))
    elif path_to_config.suffix.lower() != '.json' or not path_to_config.is_file():
        raise ValueError('{} is not .json config file'.format(path_to_config))

    model_configs = load_json(path_to_config)

    path_to_data = model_configs['path_to_data']
    train_model = model_configs['train_model']
    workers_num = model_configs['workers_num']
    batch_size = model_configs['batch_size']
    data_loaders = get_data_loaders(path_to_data, batch_size, workers_num)

    model = CustomResnet18(True)
    criterion = nn.BCEWithLogitsLoss(reduction=None)
    metric = None


    device = 'cpu'
    device_count = 0
    if cuda.is_available() and model_configs['cuda_usage']:
        device = 'cuda'
        device_count = cuda.device_count()

    criterion.to(device)
    metric.to(device)

    if device is not 'cpu' and device_count > 1:
        model = nn.DataParallel(model).cuda()
    elif device is not 'cpu':
        model = model.cuda()

    optimizer = optim.SGD(model.parameters(), lr=model_configs['learning_rate'], momentum=0.9)

    info_paths = model_configs['info_paths']

    writer = SummaryWriter(logdir=info_paths['log_dir'])
    total_epochs = model_configs['epochs']

    for epoch in range(total_epochs):
        model.train()
        train(model, data_loaders['train'], epoch, optimizer, criterion, metric, writer, device=device)
        model.val()
        val(model, criterion, metric, data_loaders['val'], epoch, writer, device=device)



if __name__ == '__main__':
    main()
