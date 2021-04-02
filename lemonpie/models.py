# AUTOGENERATED! DO NOT EDIT! File to edit: 07_models.ipynb (unless otherwise specified).

__all__ = ['dropout_mask', 'InputDropout', 'linear_layer', 'create_linear_layers', 'init_lstm', 'EHR_LSTM', 'init_cnn',
           'conv_layer', 'EHR_CNN']

# Cell
from .basics import *
from .preprocessing.vocab import * #for loading vocabs
from .preprocessing.transform import * #for loading ptlist thru EHRData
from .data import * #for EHRData
from .learn import * #for fit/predict stuff
from .metrics import * #for auroc_score
from fastai.imports import *

# Cell
def dropout_mask(x, sz, p):
    '''Dropout mask as described in fast.ai'''
    return x.new(*sz).bernoulli_(1-p).div_(1-p)

class InputDropout(nn.Module):
    '''InputDropout - same as RNNDropout described in fast.ai'''
    def __init__(self, p=0.5):
        super().__init__()
        self.p=p

    def forward(self, x):
        if not self.training or self.p == 0.: return x
        m = dropout_mask(x.data, (x.size(0), 1, x.size(2)), self.p)
        return x * m

# Cell
def linear_layer(in_features, out_features, bn=False, dropout_p=0.0):
    '''Create a single linear layer'''
    layer = [nn.Linear(in_features, out_features)]
    if bn: layer.append(nn.BatchNorm1d(out_features))
    layer.append(nn.ReLU(inplace=True))
    layer.append(nn.Dropout(dropout_p))
    return layer

def create_linear_layers(in_features_start, num_layers, bn=False, dropout_p=0.0):
    '''Create linear layers'''
    layers = []

    for l in range(num_layers):
        in_features = in_features_start if l==0 else out_features
        out_features = in_features * 2
        layers.extend(linear_layer(in_features, out_features, bn, dropout_p))

    return out_features, nn.Sequential(*layers)

# Cell
def init_lstm(m, initrange, zero_bn=False):
    '''Initialize LSTM'''
    if isinstance(m, (nn.Embedding, nn.EmbeddingBag)): m.weight.data.uniform_(-initrange, initrange)
    if isinstance(m, (nn.LSTM, nn.Linear)):
        for name, param in m.named_parameters():
                if 'bias' in name:
                    nn.init.constant_(param, 0.0)
                elif 'weight' in name:
                    nn.init.kaiming_normal_(param)
    if isinstance(m, (nn.BatchNorm1d)): nn.init.constant_(m.weight, 0. if zero_bn else 1.)
    for l in m.children(): init_lstm(l, initrange, zero_bn)

# Cell
from fastai.layers import BatchNorm1dFlat
class EHR_LSTM(nn.Module):
    '''Based on LSTM described in this paper - https://arxiv.org/abs/1801.07860'''

    def __init__(self, demograph_dims, rec_dims, demograph_wd, rec_wd, num_labels, lstm_layers=4, linear_layers=4,
                 initrange=0.3, bn=False, input_drp=0.3, lstm_drp=0.3, linear_drp=0.3, zero_bn=False):

        super().__init__()

        self.embs  = nn.ModuleList([nn.Embedding(*dim) for dim in demograph_dims])
        self.embgs = nn.ModuleList([nn.EmbeddingBag(*dim) for dim in rec_dims])

        self.rec_wd        = rec_wd
        self.demograph_wd  = demograph_wd
        self.nh            = rec_wd
        self.lstm_layers   = lstm_layers
        self.bn            = bn
        lin_features_start = (demograph_wd + 1) + rec_wd #adding 1 for age_now


        self.input_dp = InputDropout(input_drp)
        self.lstm     = nn.LSTM(input_size=self.nh, hidden_size=self.nh, num_layers=lstm_layers, batch_first=True, dropout=lstm_drp)
        if bn: self.lstm_bn = BatchNorm1dFlat(self.nh) #fastai - `nn.BatchNorm1d`, but first flattens leading dimensions
        out, self.lin = create_linear_layers(lin_features_start, linear_layers, bn, linear_drp)
        self.lin_o    = nn.Linear(out, num_labels)

        init_lstm(self, initrange, zero_bn)


    def get_embs(self, ptbatch_recs, ptbatch_demogs, x):
        for p in range(len(x)): #for the batch of pts
            ptbatch_recs[p] = torch.cat((self.embgs[0](x[p].obs_nums,x[p].obs_offsts),
                                         self.embgs[1](x[p].alg_nums,x[p].alg_offsts),
                                         self.embgs[2](x[p].crpl_nums,x[p].crpl_offsts),
                                         self.embgs[3](x[p].med_nums,x[p].med_offsts),
                                         self.embgs[4](x[p].img_nums,x[p].img_offsts),
                                         self.embgs[5](x[p].proc_nums,x[p].proc_offsts),
                                         self.embgs[6](x[p].cnd_nums,x[p].cnd_offsts),
                                         self.embgs[7](x[p].imm_nums,x[p].imm_offsts)),
                                        dim=1) #for the entire age span, example all 20 yrs
            ptbatch_demogs[p] = torch.cat((self.embs[0](x[p].demographics[0]),
                                           self.embs[1](x[p].demographics[1]),
                                           self.embs[2](x[p].demographics[2]),
                                           self.embs[3](x[p].demographics[3]),
                                           self.embs[4](x[p].demographics[4]),
                                           self.embs[5](x[p].demographics[5]),
                                           self.embs[6](x[p].demographics[6]),
                                           self.embs[7](x[p].demographics[7]),
                                           self.embs[8](x[p].demographics[8]),
                                           self.embs[9](x[p].demographics[9]),
                                           self.embs[10](x[p].demographics[10]),
                                           x[p].age_now))

        return ptbatch_recs, ptbatch_demogs

    def forward(self, x):

        bs   = len(x)
        bptt = len(x[0].obs_offsts)
        h    = torch.zeros(self.lstm_layers,bs,self.nh, device=DEVICE)

        ptbatch_recs   = torch.empty(bs,bptt,self.rec_wd, device=DEVICE)
        ptbatch_demogs = torch.empty(bs,self.demograph_wd+1, device=DEVICE)
        ptbatch_recs, ptbatch_demogs = self.get_embs(ptbatch_recs, ptbatch_demogs, x)

        ptbatch_recs = self.input_dp(ptbatch_recs)                                     #apply input dropout

        res,_ = self.lstm(ptbatch_recs, (h,h))
        res   = self.lstm_bn(res[:,-1]) if self.bn else res[:,-1]                      #lstm output
        res   = self.lin(torch.cat((res, ptbatch_demogs), dim=1))                      #concat demographics + send thru linear lyrs
        out   = self.lin_o(res)

        return out

# Cell
def init_cnn(m, initrange, zero_bn=False):
    '''Initialize CNN as described in fast.ai'''
    if getattr(m, 'bias', None) is not None: nn.init.constant_(m.bias, 0)
    if isinstance(m, (nn.Embedding, nn.EmbeddingBag)): m.weight.data.uniform_(-initrange, initrange)
    if isinstance(m, (nn.Conv2d, nn.Linear)): nn.init.kaiming_normal_(m.weight)
    if isinstance(m, (nn.BatchNorm1d, nn.BatchNorm2d)): nn.init.constant_(m.weight, 0. if zero_bn else 1.)
    for l in m.children(): init_cnn(l, initrange, zero_bn)

def conv_layer(in_channels, out_channels, kernel_size, stride=1, padding=1, bn=False):
    '''Create a single conv layer - as described in fast.ai'''
    layer = [nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, bias=not bn)]
    if bn: layer.append(nn.BatchNorm2d(out_channels))
    layer.append(nn.ReLU(inplace=True))
    return layer

# Cell
class EHR_CNN(nn.Module):
    '''Based on the model described in the Deepr paper - https://arxiv.org/abs/1607.07519'''
    def __init__(self, demograph_dims, rec_dims, demograph_wd, rec_wd, num_labels, linear_layers=4,
                 initrange=0.3, bn=False, input_drp=0.3, linear_drp=0.3, zero_bn=False):

        super().__init__()

        self.embs  = nn.ModuleList([nn.Embedding(*dim) for dim in demograph_dims])
        self.embgs = nn.ModuleList([nn.EmbeddingBag(*dim) for dim in rec_dims])

        self.rec_wd        = rec_wd
        self.demograph_wd  = demograph_wd
        self.bn            = bn
        lin_features_start = (demograph_wd + 1) + 512 #adding 1 for 'age_now', 512 = cnn output


        self.input_dp = InputDropout(input_drp)

        out, self.lin = create_linear_layers(lin_features_start, linear_layers, bn, linear_drp)
        self.lin_o    = nn.Linear(out, num_labels)

        self.cnn = nn.Sequential(
        *conv_layer(in_channels=1, out_channels=2, kernel_size=(5,5), padding=2, bn=self.bn),
        *conv_layer(2,4,kernel_size=(3,3), padding=1, bn=self.bn),
        *conv_layer(4,8,kernel_size=3, stride=2, padding=1, bn=self.bn),
        *conv_layer(8,16,kernel_size=3, stride=2, padding=1, bn=self.bn),
        *conv_layer(16,32,kernel_size=3, stride=2, padding=1, bn=self.bn),
        nn.AdaptiveMaxPool2d((4,4)),
        nn.Flatten()
        )

        init_cnn(self, initrange, zero_bn)


    def get_embs(self, ptbatch_recs, ptbatch_demogs, x):
        for p in range(len(x)): #for the batch of pts
            ptbatch_recs[p] = torch.cat((self.embgs[0](x[p].obs_nums,x[p].obs_offsts),
                                         self.embgs[1](x[p].alg_nums,x[p].alg_offsts),
                                         self.embgs[2](x[p].crpl_nums,x[p].crpl_offsts),
                                         self.embgs[3](x[p].med_nums,x[p].med_offsts),
                                         self.embgs[4](x[p].img_nums,x[p].img_offsts),
                                         self.embgs[5](x[p].proc_nums,x[p].proc_offsts),
                                         self.embgs[6](x[p].cnd_nums,x[p].cnd_offsts),
                                         self.embgs[7](x[p].imm_nums,x[p].imm_offsts)),
                                        dim=1) #for the entire age span, example all 20 yrs
            ptbatch_demogs[p] = torch.cat((self.embs[0](x[p].demographics[0]),
                                           self.embs[1](x[p].demographics[1]),
                                           self.embs[2](x[p].demographics[2]),
                                           self.embs[3](x[p].demographics[3]),
                                           self.embs[4](x[p].demographics[4]),
                                           self.embs[5](x[p].demographics[5]),
                                           self.embs[6](x[p].demographics[6]),
                                           self.embs[7](x[p].demographics[7]),
                                           self.embs[8](x[p].demographics[8]),
                                           self.embs[9](x[p].demographics[9]),
                                           self.embs[10](x[p].demographics[10]),
                                           x[p].age_now))

        return ptbatch_recs, ptbatch_demogs

    def forward(self, x):

        bs     = len(x)
        height = len(x[0].obs_offsts)
        width  = self.rec_wd

        ptbatch_recs   = torch.empty(bs,height,width, device=DEVICE)
        ptbatch_demogs = torch.empty(bs,self.demograph_wd+1, device=DEVICE)

        ptbatch_recs, ptbatch_demogs = self.get_embs(ptbatch_recs, ptbatch_demogs, x)
        ptbatch_recs = self.input_dp(ptbatch_recs)                                    #apply input dropout

        res = self.cnn(ptbatch_recs.reshape(bs,1,height,width))                       #cnn output
        res   = self.lin(torch.cat((res, ptbatch_demogs), dim=1))                     #concat demographics + send thru linear lyrs
        out   = self.lin_o(res)

        return out