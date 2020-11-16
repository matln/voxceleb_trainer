#!/usr/bin/python
#-*- coding: utf-8 -*-

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy, math, pdb, sys, random
import time, os, itertools, shutil, importlib
from tuneThreshold import tuneThresholdfromScore
from DatasetLoader import loadWAV

class SpeakerNet(nn.Module):

<<<<<<< HEAD
    def __init__(self, max_frames, lr = 0.0001, margin = 1, scale = 1, hard_rank = 0, 
                 hard_prob = 0, model="alexnet50", nOut = 512, nSpeakers = 1000, 
                 optimizer = 'adam', encoder_type = 'SAP', normalize = True, 
                 trainfunc='contrastive', **kwargs):
        super(SpeakerNet, self).__init__()

        argsdict = {'nOut': nOut, 'encoder_type':encoder_type}

        SpeakerNetModel = importlib.import_module('models.'+model).__getattribute__(model)
        self.__S__ = SpeakerNetModel(**argsdict).cuda()

        if trainfunc == 'angleproto':
            self.__L__ = AngleProtoLoss().cuda()
            self.__train_normalize__    = True
            self.__test_normalize__     = True
        elif trainfunc == 'ge2e':
            self.__L__ = GE2ELoss().cuda()
            self.__train_normalize__    = True
            self.__test_normalize__     = True
        elif trainfunc == 'amsoftmax':
            self.__L__ = AMSoftmax(in_feats=nOut, n_classes=nSpeakers, m=margin, s=scale).cuda()
            self.__train_normalize__    = False
            self.__test_normalize__     = True
        elif trainfunc == 'aamsoftmax':
            self.__L__ = AAMSoftmax(in_feats=nOut, n_classes=nSpeakers, m=margin, s=scale).cuda()
            self.__train_normalize__    = False
            self.__test_normalize__     = True
        elif trainfunc == 'softmax':
            self.__L__ = SoftmaxLoss(in_feats=nOut, n_classes=nSpeakers).cuda()
            self.__train_normalize__    = False
            self.__test_normalize__     = True
        elif trainfunc == 'proto':
            self.__L__ = ProtoLoss().cuda()
            self.__train_normalize__    = False
            self.__test_normalize__     = False
        elif trainfunc == 'triplet':
            self.__L__ = PairwiseLoss(loss_func='triplet', hard_rank=hard_rank, hard_prob=hard_prob, margin=margin).cuda()
            self.__train_normalize__    = True
            self.__test_normalize__     = True
        elif trainfunc == 'contrastive':
            self.__L__ = PairwiseLoss(loss_func='contrastive', hard_rank=hard_rank, hard_prob=hard_prob, margin=margin).cuda()
            self.__train_normalize__    = True
            self.__test_normalize__     = True
        else:
            raise ValueError('Undefined loss.')

        if optimizer == 'adam':
            self.__optimizer__ = torch.optim.Adam(self.parameters(), lr = lr);
        elif optimizer == 'sgd':
            self.__optimizer__ = torch.optim.SGD(self.parameters(), lr = lr, momentum = 0.9, weight_decay=5e-5);
        else:
            raise ValueError('Undefined optimizer.')
        
        self.__max_frames__ = max_frames;
=======
    def __init__(self, model, optimizer, scheduler, trainfunc, **kwargs):
        super(SpeakerNet, self).__init__();

        SpeakerNetModel = importlib.import_module('models.'+model).__getattribute__('MainModel')
        self.__S__ = SpeakerNetModel(**kwargs).cuda();

        LossFunction = importlib.import_module('loss.'+trainfunc).__getattribute__('LossFunction')
        self.__L__ = LossFunction(**kwargs).cuda();

        Optimizer = importlib.import_module('optimizer.'+optimizer).__getattribute__('Optimizer')
        self.__optimizer__ = Optimizer(self.parameters(), **kwargs)

        Scheduler = importlib.import_module('scheduler.'+scheduler).__getattribute__('Scheduler')
        self.__scheduler__, self.lr_step = Scheduler(self.__optimizer__, **kwargs)

        assert self.lr_step in ['epoch', 'iteration']
>>>>>>> 6d3db45cbe00c27df71d6b04ca5fec0edc5317ac

    ## ===== ===== ===== ===== ===== ===== ===== =====
    ## Train network
    ## ===== ===== ===== ===== ===== ===== ===== =====

    def train_network(self, loader):

        self.train();

        stepsize = loader.batch_size;

        counter = 0;
        index   = 0;
        loss    = 0;
        top1    = 0     # EER or accuracy

        tstart = time.time()
        
        for data, data_label in loader:

            data = data.transpose(0,1)

            self.zero_grad();

            feat = []
            for inp in data:
                outp      = self.__S__.forward(inp.cuda())
                feat.append(outp)

            feat = torch.stack(feat,dim=1).squeeze()

            label   = torch.LongTensor(data_label).cuda()

            nloss, prec1 = self.__L__.forward(feat,label)

            loss    += nloss.detach().cpu();
            top1    += prec1
            counter += 1;
            index   += stepsize;

            nloss.backward();
            self.__optimizer__.step();

            telapsed = time.time() - tstart
            tstart = time.time()

            sys.stdout.write("\rProcessing (%d) "%(index));
            sys.stdout.write("Loss %f TEER/TAcc %2.3f%% - %.2f Hz "%(loss/counter, top1/counter, stepsize/telapsed));
            sys.stdout.flush();

            if self.lr_step == 'iteration': self.__scheduler__.step()

        if self.lr_step == 'epoch': self.__scheduler__.step()

        sys.stdout.write("\n");
        
        return (loss/counter, top1/counter);


    ## ===== ===== ===== ===== ===== ===== ===== =====
    ## Evaluate from list
    ## ===== ===== ===== ===== ===== ===== ===== =====

    def evaluateFromList(self, listfilename, print_interval=100, test_path='', num_eval=10, eval_frames=None):
        
        self.eval();
        
        lines       = []
        files       = []
        feats       = {}
        tstart      = time.time()

        ## Read all lines
        with open(listfilename) as listfile:
            while True:
                line = listfile.readline();
                if (not line):
                    break;

                data = line.split();

                ## Append random label if missing
                if len(data) == 2: data = [random.randint(0,1)] + data

                files.append(data[1])
                files.append(data[2])
                lines.append(line)

        setfiles = list(set(files))
        setfiles.sort()

        ## Save all features to file
        for idx, file in enumerate(setfiles):

            inp1 = torch.FloatTensor(loadWAV(os.path.join(test_path,file), eval_frames, evalmode=True, num_eval=num_eval)).cuda()

            ref_feat = self.__S__.forward(inp1).detach().cpu()

            filename = '%06d.wav'%idx

            feats[file]     = ref_feat

            telapsed = time.time() - tstart

            if idx % print_interval == 0:
                sys.stdout.write("\rReading %d of %d: %.2f Hz, embedding size %d"%(idx,len(setfiles),idx/telapsed,ref_feat.size()[1]));

        print('')
        all_scores = [];
        all_labels = [];
        all_trials = [];
        tstart = time.time()

        ## Read files and compute all scores
        for idx, line in enumerate(lines):

            data = line.split();

            ## Append random label if missing
            if len(data) == 2: data = [random.randint(0,1)] + data

            ref_feat = feats[data[1]].cuda()
            com_feat = feats[data[2]].cuda()

            if self.__L__.test_normalize:
                ref_feat = F.normalize(ref_feat, p=2, dim=1)
                com_feat = F.normalize(com_feat, p=2, dim=1)

            dist = F.pairwise_distance(ref_feat.unsqueeze(-1), com_feat.unsqueeze(-1).transpose(0,2)).detach().cpu().numpy();

            score = -1 * numpy.mean(dist);

            all_scores.append(score);  
            all_labels.append(int(data[0]));
            all_trials.append(data[1]+" "+data[2])

            if idx % print_interval == 0:
                telapsed = time.time() - tstart
                sys.stdout.write("\rComputing %d of %d: %.2f Hz"%(idx,len(lines),idx/telapsed));
                sys.stdout.flush();

        print('\n')

        return (all_scores, all_labels, all_trials);


    ## ===== ===== ===== ===== ===== ===== ===== =====
    ## Save parameters
    ## ===== ===== ===== ===== ===== ===== ===== =====

    def saveParameters(self, path):
        
        torch.save(self.state_dict(), path);


    ## ===== ===== ===== ===== ===== ===== ===== =====
    ## Load parameters
    ## ===== ===== ===== ===== ===== ===== ===== =====

    def loadParameters(self, path):

        self_state = self.state_dict();
        loaded_state = torch.load(path);
        for name, param in loaded_state.items():
            origname = name;
            if name not in self_state:
                name = name.replace("module.", "");

                if name not in self_state:
                    print("%s is not in the model."%origname);
                    continue;

            if self_state[name].size() != loaded_state[origname].size():
                print("Wrong parameter length: %s, model: %s, loaded: %s"%(origname, self_state[name].size(), loaded_state[origname].size()));
                continue;

            self_state[name].copy_(param);

