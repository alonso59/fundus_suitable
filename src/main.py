'''asd'''
import os
import yaml
import argparse
import numpy as np
import cv2
from PIL import Image
from tqdm import tqdm
import os
from common.utils import get_filenames, create_dir
from classification.train import train as clsf_train
from preprocessing.train import train as pre_train
from classification.predict import implement as clsf_impl
from preprocessing.predict import implement as pre_impl
from retina_det.implement import impl as det_impl
from retina_det.train import run as det_train
import pandas as pd
import datetime

def main():
    """
    (*) default

    python src/main.py --stage  class*  --mode  train*   --config   configs/classifier.yaml* --source dataset/images/            
                                pre             eval                configs/segmenter.yaml            dataset/images/input.jpg               
                                det             predict             configs/detector.yaml



    python src/main.py --stage impl --source dataset/images/
                                              dataset/images/input.jpg
    """

    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', type=str, default='class',
                        help='class, pre, det, impl', required=True)
    parser.add_argument('--config', type=str, default='configs/classifier.yaml', help='config file', required=False)
    parser.add_argument('--mode', type=str, default='eval', help='train, eval, predict', required=False)
    parser.add_argument('--source', type=str, default='dataset/images', help='file or dir/, jpg, png, bmp, tiff')
    parser.add_argument('--save_results', type=bool, default=True, help='Save results in output/', required=False)
    opt = parser.parse_args()

    config = opt.config
    stage = opt.stage
    mode = opt.mode
    source = opt.source

    if stage == 'impl':
        create_dir('outputs/detection')
        create_dir('outputs/preprocessing')
        implement(source, opt.save_results)
    elif stage == 'class':
        assert config == 'configs/classifier.yaml'
        if mode == 'train':
            with open(config, "r") as ymlfile:
                cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)
            clsf_train(cfg)
    elif stage == 'pre':
        assert config == 'configs/segmenter.yaml'
        if mode == 'train':
            with open(config, "r") as ymlfile:
                cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)
            pre_train(cfg)
    elif stage == 'det':
        assert config == 'configs/detector.yaml'
        if mode == 'train':
            with open(config, "r") as ymlfile:
                cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)
            det_train(batch=cfg['batch_size'], epochs=cfg['epochs'], weights=cfg['model_pretrain'],
                      data=opt.config, imgsz=224, save_dir='logs/detection/train/')
        # python path/to/train.py --data coco128.yaml --weights yolov5s.pt --img 640
        pass
    else:
        raise RuntimeError('Mode/stage combination not implemented!')


def implement(source, save_results=True):
    preprocessing_weights = 'pretrain/unet_weights.pth'
    classifier_weights = 'pretrain/drnetq_weights.pth'
    detector_wieghts = 'pretrain/retina_detection.pt'

    with open('configs/segmenter.yaml', "r") as ymlfile:
        cfg_seg = yaml.load(ymlfile, Loader=yaml.FullLoader)
    with open('configs/classifier.yaml', "r") as ymlfile:
        cfg_clas = yaml.load(ymlfile, Loader=yaml.FullLoader)
    with open('configs/detector.yaml', "r") as ymlfile:
        cfg_ob = yaml.load(ymlfile, Loader=yaml.FullLoader)
    ext = 'jpg', 'jpeg', 'tiff', 'tif', 'png', 'bmp', 'JPEG', 'JPG', 'PNG'
    if os.path.isdir(source):
        X0 = get_filenames(source, ext)
    else:
        X0 = source,

    classification = []
    macula = []
    od = []
    suitability = []
    filename = []

    for i in tqdm(X0):
        # Preprocessing
        crop, pred_crop = pre_impl(source=i, config=cfg_seg, weights=preprocessing_weights,
                              img_size=cfg_seg['general']['img_size'], n_classes=1, device='cuda')

        crop1, pred_crop = Image.fromarray(crop), Image.fromarray(pred_crop)

        if save_results:
            crop1.save('outputs/preprocessing4/' + os.path.split(i)[1])
        
        crop1 = crop1.resize((224, 224))
        
        # classification
        pred_class, y_pr = clsf_impl(source=np.array(crop1),
                         model_name=cfg_clas['model_name'],
                         weights=classifier_weights, img_size=cfg_clas['general']['img_size'],
                         n_classes=cfg_clas['general']['n_classes'],
                         device='cuda')

        classification.append(pred_class)

        # Detection
        pred_det, mac, disk = det_impl(weights=detector_wieghts, source=crop, imgsz=(224, 224))  # detector
        macula.append(mac)
        od.append(disk)
        suit = 0
        if pred_class == 1 and mac > 0 and disk > 0:
            suit = 1
            suitability.append(suit)
            text_suitable = 'High suitability confidence'
            fontColor = (100,255,100)
        else:
            suitability.append(suit)
            text_suitable = 'Low suitability confidence'
            fontColor = (255,100,100)
        if save_results:
            pred_copy = pred_det
            # Write some Text
            font                   = cv2.FONT_HERSHEY_SIMPLEX
            bottomLeftCornerOfText = (10, 100)
            thickness              = 6
            lineType               = 3
            
            cv2.putText(pred_copy, text_suitable, 
                bottomLeftCornerOfText, 
                font, 
                (pred_copy.shape[0] / pred_copy.shape[1]) * 5,
                fontColor,
                thickness,
                lineType)
            cv2.putText(pred_copy, f'Quality Class:{pred_class} Conf:{y_pr:0.4f}', 
                (10, 400), 
                font, 
                (pred_copy.shape[0] / pred_copy.shape[1]) * 5,
                (100,100,255),
                thickness,
                lineType)
            pred_copy = Image.fromarray(pred_copy)
            pred_copy.save('outputs/detection4/' + os.path.split(i)[1])
        
        
        filename.append(os.path.split(i)[1])
    
    df = pd.DataFrame({'Filename': filename,
                        'Classification': classification,
                        'Macula conf': macula,
                        'OD conf': od,
                        'Suitability': suitability}
                        )
    now = datetime.datetime.now()
    df.to_csv('outputs/' + str(now.strftime("%Y-%m-%d_%H_%M_%S")) + '.csv',index=False)
    return pred_det, crop

if __name__ == '__main__':
    # try:
    main()
    # except Exception as ex:
    #     print(ex)
