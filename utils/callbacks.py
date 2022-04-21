from torch.utils.tensorboard import SummaryWriter
import torch
from torchvision.utils import draw_segmentation_masks as drawer 
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.image import show_cam_on_image
import sys
from PIL import Image
import numpy as np

class TensorboardWriter():

    def __init__(self, metric, name_dir):

        super().__init__()
        self.writer = SummaryWriter(log_dir=name_dir)
        self.metric = metric

    def per_epoch(self, train_loss, val_loss, train_metric, val_metric, step):
        results_loss = {'Train': train_loss, 'Val': val_loss}
        results_metric = {'Train': train_metric, 'Val': val_metric}
        self.writer.add_scalars("Loss", results_loss, step)
        self.writer.add_scalars('Acc', results_metric, step)

    def per_iter(self, loss, metric, step, name):
        self.writer.add_scalar(f"{name}/Loss", loss, step)
        self.writer.add_scalar(f'{name}/Acc', metric, step)

    def learning_rate(self, lr_, step):
        self.writer.add_scalar("lr", lr_, step)

    def save_graph(self, model, loader):
        self.writer.add_graph(model, loader)

    def save_text(self, tag, text_string):
        self.writer.add_text(tag=tag, text_string=text_string)

    def save_img_preds(self, model, layer_target, input_tensor, label, step, device):
        if label == 0:
            pred = grad_cam(model, layer_target, input_tensor, device)
            self.writer.add_images(f'Class0', pred, step, dataformats='HWC')
        if label == 1:
            pred = grad_cam(model, layer_target, input_tensor, device)
            self.writer.add_images(f'Class1', pred, step, dataformats='HWC')

    def save_figure(self, name, img, step):
        self.writer.add_figure(name, img, step)

    def save_text(self, text):
        self.writer.add_text('Logs', text)

def image_tensorboard(img, device):
    img_rgb = torch.zeros(img.size(), device=device)
    img_rgb = torch.div(img, img.max().item())
    return img_rgb

def grad_cam(model, layer_target, input_tensor, device):
    # try:
    #     cam = GradCAM(model, layer_target, use_cuda=True)
    # except:
    cam = GradCAM(model, layer_target, use_cuda=True, reshape_transform=reshape_transform)
    rgb = input_tensor.detach().cpu()
    grayscale_cam = cam(input_tensor=rgb.unsqueeze(0), targets=None)
    grayscale_cam = grayscale_cam[0, :]
    visualization = show_cam_on_image(rgb.numpy().transpose(1, 2, 0), grayscale_cam, use_rgb=True)
    vis_img = np.array(Image.fromarray(visualization).convert('RGB')) / 255.
    
    vis_tensor = torch.tensor(vis_img, dtype=torch.float, device=device)
    return vis_tensor

def reshape_transform(tensor, height=7, width=7):
    
    # result = tensor.reshape(tensor.size(0), height, width, tensor.size(2))

    # Bring the channels to the first dimension,
    # like in CNNs.
    result = tensor.transpose(2, 3).transpose(1, 2)
    return result
