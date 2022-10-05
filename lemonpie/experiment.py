# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/08_experiment.ipynb (unless otherwise specified).

__all__ = ['get_data', 'get_optimizer', 'get_model', 'Experiment']

# Cell
from .basics import * #for GVs
from .preprocessing.vocab import * #for loading vocabs
from .preprocessing.transform import * #for loading ptlist thru EHRData
from .data import * #for EHRData
from .learn import * #for RunHistory
from .metrics import * #for auroc_score
from .models import * #for the models
from fastai.imports import *

# Cell
from addict import Dict
import pprint
import sys

# Cell
def get_data(params, for_training=True):
    '''Convenience fn to get data (for training or testing) based on `data_params` in `experiment.yaml`'''
    ehr_data = EHRData(params.dataset_path, params.labels, params.age_start, params.age_stop, params.age_in_months, params.lazy_load_gpu)
    if for_training:
        return ehr_data.get_data(params.bs, params.num_workers)
    else:
        return ehr_data.get_test_data(params.bs, params.num_workers)

# Cell
def get_optimizer(model, params):
    '''Convenience fn to get optimizer based on `optim_params` in `experiment.yaml'''
    if   params.optim == 'SGD' : optimizer = optim.SGD(model.parameters(), lr=0.001)
    elif params.optim == 'Adam': optimizer = optim.Adam(model.parameters())
    else                       : optimizer = optim.Adagrad(model.parameters(), params.lr, params.lr_decay, params.weight_decay)
    return optimizer

# Cell
def get_model(dataset_path, num_labels, params):
    '''Convenience fn to get model based on `model_params` in `experiment.yaml'''
    demograph_dims, rec_dims, demograph_dims_wd, rec_dims_wd = get_all_emb_dims(EhrVocabList.load(dataset_path), params.αd)

    if params.model == 'LSTM':
        model = EHR_LSTM(demograph_dims, rec_dims, demograph_dims_wd, rec_dims_wd, num_labels,
                         params.lstm_layers, params.linear_layers, params.initrange, params.bn,
                         params.input_drp, params.lstm_drp, params.linear_drp, params.zero_bn)
    elif params.model == 'CNN':
        model = EHR_CNN(demograph_dims, rec_dims, demograph_dims_wd, rec_dims_wd, num_labels,
                        params.linear_layers, params.initrange, params.bn,
                        params.input_drp, params.linear_drp, params.zero_bn)
    return model.to(DEVICE)

# Cell
class Experiment:
    '''A simple (bare bones) Experiment class for experiment management'''
    def __init__(self, name, config, params):
        self.name = name
        self.desc = config.desc
        self.path = Path(f'{config.path}/{name}')
        self.chkpt_path = Path(f'{config.checkpoint_path}/{name}')
        self.labels = params.data_params.labels
        self.config, self.params = config, params
        self.history = RunHistory(self.labels)

    def __repr__(self):
        '''Print out Experiment details'''
        if sys.version_info[1]>=8: pp = pprint.PrettyPrinter(indent=2, compact=True, sort_dicts=False)
        else:                      pp = pprint.PrettyPrinter(indent=2, compact=True)
        res = f'{pp.pformat(self.config)}\n'
        res += pp.pformat(self.params)
        return res

    def save(self):
        '''Save the Experiment'''
        self.path.mkdir(parents=True, exist_ok=True)
        with open(f'{self.path}/{self.name}.experiment', 'wb')  as f:
            pickle.dump(self, f)
        print(f'Saved experiment to {self.path}/{self.name}.experiment')

        yaml_file = Path(f'{self.path}/experiment.yaml')
        if not yaml_file.exists():
            print('No experiment settings file found, so creating it ..')
            exp = Dict(config=self.config, params=self.params)
            with open(yaml_file, 'w') as e:
                yaml.dump(exp.to_dict(), e, sort_keys=False, allow_unicode=True)
            print(f'Saved experiment settings to {yaml_file}')

    @classmethod
    def load(cls, name, path=None):
        '''Load an existing Experiment'''
        exp_dir = Path(f'{EXPERIMENT_STORE}/{name}') if path == None else Path(f'{path}/{name}')
        with open(f'{exp_dir}/{name}.experiment','rb') as infile:
            exp = pickle.load(infile)
        print(f'Loaded experiment from {exp_dir}/{name}.experiment')
        return exp

    @classmethod
    def create(cls, exp_name, desc, dataset_path, labels, optim, model,
               exp_path='default_exp_store', checkpoint_path='default_model_store',
               age_start=0, age_stop=20, age_in_months=False, lazy_load_gpu=True, bs=128, num_workers=0,
               lr=0.01, lr_decay=0, weight_decay=0,
               αd=0.5736, linear_layers=4, initrange=0.3, bn=False, input_drp=0.3, linear_drp=0.3,
               lstm_layers=4, lstm_drp=0.3, zero_bn=False):
        '''Create a *new* Experiment object'''
        template = {
            'config':
            {
                'name': exp_name,
                'path': EXPERIMENT_STORE if exp_path=='default_exp_store' else exp_path,
                'desc': desc,
                'checkpoint_path': MODEL_STORE if checkpoint_path=='default_model_store' else checkpoint_path
            },
            'params':
            {
                'data_params':
                {
                    'dataset_path': dataset_path,
                    'labels': labels,
                    'age_start': age_start,
                    'age_stop': age_stop,
                    'age_in_months': age_in_months,
                    'bs': bs,
                    'num_workers': num_workers,
                    'lazy_load_gpu': lazy_load_gpu
                },
                'optim_params':
                {
                    'optim': optim,
                    'lr': lr,
                    'lr_decay': lr_decay,
                    'weight_decay': weight_decay
                },
                'model_params':
                {
                    'model': model,
                    'αd': αd,
                    'linear_layers': linear_layers,
                    'initrange': initrange,
                    'bn': bn,
                    'input_drp': input_drp,
                    'linear_drp': linear_drp,
                    'zero_bn': zero_bn,
                    'lstm_layers': None if model=='CNN' else lstm_layers,
                    'lstm_drp': None if model=='CNN' else lstm_drp
                }
            }
        }
        exp = Dict(template)
        return cls(exp_name, exp.config, exp.params)

    @classmethod
    def create_from_file(cls, path, name):
        '''Create a *new* Experiment object from the `experiment.yaml` file in the `path/name` directory'''
        exp_dir = Path(f'{path}/{name}')
        with open(f'{exp_dir}/experiment.yaml', 'rb') as f:
            contents = yaml.full_load(f)

        exp = Dict(contents)
        return cls(name, exp.config, exp.params)

    def fit(self, epochs, from_checkpoint=False, to_checkpoint=True,  verbosity=.75, plot=True, save=True):
        '''Fit function that assembles everything needed and calls the `lemonpie.learn.fit` function'''
        train_dl, valid_dl, train_pos_wts, valid_pos_wts = get_data(self.params.data_params)
        model = get_model(self.params.data_params.dataset_path, len(self.params.data_params.labels), self.params.model_params)
        train_loss_fn, valid_loss_fn = get_loss_fn(train_pos_wts), get_loss_fn(valid_pos_wts)
        optim = get_optimizer(model, self.params.optim_params)
        lazy = self.params.data_params.lazy_load_gpu
        from_chkpt_path = self.chkpt_path if from_checkpoint else None
        to_chkpt_path   = self.chkpt_path if to_checkpoint   else None

        self.history = fit(epochs, self.history, model, train_loss_fn, valid_loss_fn, optim,
                           auroc_score, train_dl, valid_dl, lazy, to_chkpt_path, from_chkpt_path, verbosity)
        if plot: plot_fit_results(self.history, self.labels)
        if save: self.save()

    def predict(self, plot=True, save=True):
        '''Predict function that assembles everything needed and calls the `lemonpie.learn.predict` function'''
        test_dl, test_pos_wts = get_data(self.params.data_params, for_training=False)
        model = get_model(self.params.data_params.dataset_path, len(self.params.data_params.labels), self.params.model_params)
        test_loss_fn = get_loss_fn(test_pos_wts)
        lazy = self.params.data_params.lazy_load_gpu

        self.history = predict(self.history, model, test_loss_fn, auroc_score, test_dl, self.chkpt_path, lazy)
        self.history = summarize_prediction(self.history, self.labels, plot)
        if save: self.save()