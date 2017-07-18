import copy
import torch
import torch.nn as nn
import torchvision.models as pytorch_models

import sys
sys.path.append('vqa/external/pretrained-models.pytorch')
import pretrainedmodels as torch7_models

pytorch_resnet_names = sorted(name for name in pytorch_models.__dict__
    if name.islower()
    and name.startswith("resnet")
    and callable(pytorch_models.__dict__[name]))

torch7_resnet_names = sorted(name for name in torch7_models.__dict__
    if name.islower()
    and callable(torch7_models.__dict__[name]))

model_names = pytorch_resnet_names + torch7_resnet_names

def factory(opt, cuda=True, data_parallel=True):
    opt = copy.copy(opt)

    # forward_* will be better handle in futur release
    def forward_resnet(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)

        if 'pooling' in opt and opt['pooling']:
            x = self.avgpool(x)
            div = x.size(3) + x.size(2)
            x = x.sum(3)
            x = x.sum(2)
            x = x.view(x.size(0), -1)
            x = x.div(div)

        return x

    def forward_resnext(self, x):
        x = self.features(x)

        if 'pooling' in opt and opt['pooling']:
            x = self.avgpool(x)
            div = x.size(3) + x.size(2)
            x = x.sum(3)
            x = x.sum(2)
            x = x.view(x.size(0), -1)
            x = x.div(div)

        return x

    if opt['arch'] in pytorch_resnet_names:
        model = pytorch_models.__dict__[opt['arch']](pretrained=True)

        convnet = model # ugly hack in case of DataParallel wrapping
        model.forward = lambda x: forward_resnet(convnet, x)

    elif opt['arch'] == 'fbresnet152':
        model = torch7_models.__dict__[opt['arch']](num_classes=1000,
                                                    pretrained='imagenet')

        convnet = model # ugly hack in case of DataParallel wrapping
        model.forward = lambda x: forward_resnet(convnet, x)

    elif opt['arch'] in torch7_resnet_names:
        model = torch7_models.__dict__[opt['arch']](num_classes=1000,
                                                    pretrained='imagenet')
        
        convnet = model # ugly hack in case of DataParallel wrapping
        model.forward = lambda x: forward_resnext(convnet, x)

    else:
        raise ValueError
    
    if data_parallel:
        model = nn.DataParallel(model).cuda()
        if not cuda:
            raise ValueError

    if cuda:
        model.cuda()

    return model