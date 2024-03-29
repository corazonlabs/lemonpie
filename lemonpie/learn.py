# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/06_learn.ipynb (unless otherwise specified).

__all__ = ['save_to_checkpoint', 'load_from_checkpoint', 'get_loss_fn', 'RunHistory', 'train', 'evaluate', 'fit',
           'predict', 'plot_loss', 'plot_losses', 'plot_aurocs', 'plot_train_valid_aurocs', 'plot_fit_results',
           'summarize_prediction', 'count_parameters']

# Cell
from .basics import *
from .metrics import *
from fastai.imports import *

# Cell
def save_to_checkpoint(epoch_index, model, optimizer, path):
    '''Save model and optimizer state_dicts to checkpoint'''
    if not os.path.isdir(path): Path(path).mkdir(parents=True, exist_ok=True)
    torch.save({
        'epoch_index':epoch_index,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict()
        }, f'{path}/checkpoint.tar')
    print(f'Checkpointed to "{path}/checkpoint.tar"')

# Cell
def load_from_checkpoint(model, path, optimizer=None, for_inference=False):
    '''Load from checkpoint - model, optimizer & epoch_index for training or just model for inference'''

    print(f'From "{path}/checkpoint.tar", loading model ...')
    chkpt = torch.load(f'{path}/checkpoint.tar')
    model.load_state_dict(chkpt['model_state_dict'])
    model = model.to(DEVICE)

    if for_inference:
        return model
    else:
        print(f'loading optimizer and epoch_index ...')
        optimizer.load_state_dict(chkpt['optimizer_state_dict'])
        return chkpt['epoch_index'], model, optimizer

# Cell
def get_loss_fn(pos_wts):
    '''Return `nn.BCEWithLogitsLoss` with the given positive weights'''
    return nn.BCEWithLogitsLoss(pos_weight=pos_wts).to(DEVICE)

# Cell
class RunHistory:
    '''Class to hold training and prediction run histories'''
    def __init__(self, labels):
        self.train = self.valid = self.test = pd.DataFrame(columns=['loss', *labels])
        self.y_train = self.yhat_train = self.y_valid = self.yhat_valid = self.y_test = self.yhat_test = []
        self.prediction_summary = pd.DataFrame()

# Cell
def train(model, train_dl, train_loss_fn, optimizer, lazy=True, use_amp = True, scaler=None):
    '''Train model using train dataset'''
    yhat_train = y_train = Tensor([])
    train_loss = 0.
    model.train()

    for xb, yb in train_dl:
        if lazy: xb, yb = [x.to_gpu(non_block=True) for x in xb], yb.to(DEVICE, non_blocking=True)
        with torch.cuda.amp.autocast(enabled=use_amp):
            y_hat  = model(xb)
            loss   = train_loss_fn(y_hat, yb)

        train_loss += loss.item()
        yhat_train = torch.cat((yhat_train, y_hat.cpu().detach() ))
#         yhat_train = torch.cat((yhat_train, torch.sigmoid( y_hat.cpu().detach() ) )) #just for AMP testing for now
        y_train    = torch.cat((y_train, yb.cpu().detach()))

        if use_amp:
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            loss.backward()
            optimizer.step()

        model.zero_grad(set_to_none=True)

    return train_loss, yhat_train, y_train, model

# Cell
def evaluate(model, eval_dl, eval_loss_fn, lazy=True, use_amp = True):
    '''Evaluate model - used for validation (while training) and prediction'''
    yhat_eval = y_eval = Tensor([])
    eval_loss = 0.
    model.eval()

    with torch.no_grad():
        for xb, yb in eval_dl:
            if lazy: xb, yb = [x.to_gpu(non_block=True) for x in xb], yb.to(DEVICE, non_blocking=True)
            with torch.cuda.amp.autocast(enabled=use_amp):
                y_hat  = model(xb)
                loss   = eval_loss_fn(y_hat, yb)

#             eval_loss += (eval_loss_fn(y_hat, yb)).item()
            eval_loss += loss.item()
#             yhat_eval = torch.cat((yhat_eval, torch.sigmoid( y_hat.cpu().detach() ) )) # for amp testing
            yhat_eval = torch.cat((yhat_eval, y_hat.cpu().detach() ))
            y_eval    = torch.cat((y_eval, yb.cpu().detach()))

    return eval_loss, yhat_eval, y_eval

# Cell
def fit(epochs, history, model, train_loss_fn, valid_loss_fn, optimizer, accuracy_fn,
        train_dl, valid_dl, lazy=True, to_chkpt_path=None, from_chkpt_path=None, verbosity=0.75, use_amp=True):
    '''Fit model and return results in `history`'''

    if from_chkpt_path:
        last_epoch, model, optimizer = load_from_checkpoint(model, from_chkpt_path, optimizer, for_inference=False)
        start_epoch = last_epoch+1
    else:
        start_epoch = 0
    end_epoch = start_epoch+(epochs-1)
    print_epochs = np.linspace(start_epoch, end_epoch, int(epochs*verbosity), endpoint=True, dtype=int)
    train_history, valid_history = [], []

    print('{:>5} {:>16} {:^20} {:>25} {:^20}'.format('epoch |', 'train loss |', 'train aurocs', 'valid loss |', 'valid aurocs'))
    print('{:-^100}'.format('-'))

    scaler = torch.cuda.amp.GradScaler(enabled=use_amp)

    for epoch in range (start_epoch, start_epoch+epochs):

        train_loss, yhat_train, y_train, model = train(model, train_dl, train_loss_fn, optimizer, lazy, use_amp, scaler)
        valid_loss, yhat_valid, y_valid = evaluate(model, valid_dl, valid_loss_fn, lazy, use_amp)

        train_loss,   valid_loss   = train_loss/len(train_dl), valid_loss/len(valid_dl)
        train_aurocs, valid_aurocs = accuracy_fn(y_train, yhat_train), accuracy_fn(y_valid, yhat_valid)
        train_history.append([train_loss, *train_aurocs])
        valid_history.append([valid_loss, *valid_aurocs])

        if epoch in print_epochs:
            row  = f'{epoch:>5} |'
            row += f'{train_loss:>15.3f} | '
            row += f'{[f"{a:.3f}" for a in train_aurocs[:4]]}'
            row += f'{valid_loss:>19.3f} | '
            row += f'{[f"{a:.3f}" for a in valid_aurocs[:4]]}'
            print(re.sub("',*", "", row))

    if to_chkpt_path: save_to_checkpoint(end_epoch, model, optimizer, to_chkpt_path)

    h = history
    h.y_train, h.yhat_train, h.y_valid, h.yhat_valid = y_train, yhat_train, y_valid, yhat_valid
    h.train = h.train.append(pd.DataFrame(train_history, columns=h.train.columns), ignore_index=True)
    h.valid = h.valid.append(pd.DataFrame(valid_history, columns=h.valid.columns), ignore_index=True)

    return h

# Cell
def predict(history, model, test_loss_fn, accuracy_fn, test_dl, chkpt_path, lazy=True):
    '''Predict and return results in `history`'''
    model = load_from_checkpoint(model, chkpt_path, for_inference=True)
    test_loss, yhat_test, y_test = evaluate(model, test_dl, test_loss_fn, lazy)

    test_loss = test_loss/len(test_dl)
    test_aurocs = accuracy_fn(y_test, yhat_test)
    print(f'test loss = {test_loss}')
    print(f'test aurocs = {test_aurocs}')

    h = history
    h.test = pd.DataFrame([[test_loss, *test_aurocs]], columns=h.test.columns)
    h.y_test, h.yhat_test = y_test, yhat_test

    return h

# Cell
def plot_loss(history_df, title='Loss', axis=None):
    '''Plot loss'''
    if axis == None:
        fig = plt.figure(figsize=(8,5))
        axis = fig.add_axes([0,0,1,1])

    axis.plot(range(len(history_df)), history_df['loss'], label=title)

    axis.set_title(title)
    axis.set_xlabel('epochs')
    axis.set_ylabel('loss')
    axis.legend(loc=0)

# Cell
def plot_losses(train_history, valid_history):
    '''Plot multiple losses (train and valid) side by side'''
    fig, axes = plt.subplots(1,2, figsize=(15,5))
    plt.tight_layout()

    plot_loss(train_history, title='Train Loss', axis=axes[0])
    plot_loss(valid_history, title='Valid Loss', axis=axes[1])

# Cell
def plot_aurocs(history_df, title='AUROC Scores', axis=None):
    '''Plot AUROC scores'''
    if axis == None:
        fig = plt.figure(figsize=(8,5))
        axis = fig.add_axes([0,0,1,1])
    for lbl in history_df.columns[1:]:
        axis.plot(range(len(history_df)), history_df[lbl], label=f'{lbl} (final: {history_df[lbl].iat[-1]:.3f})')
    axis.set_title(title)
    axis.set_xlabel('epochs')
    axis.set_ylabel('auroc scores')
    axis.legend(loc=0)

# Cell
def plot_train_valid_aurocs(train_history, valid_history):
    '''Plot train and valid AUROC scores side by side'''
    fig, axes = plt.subplots(1,2, figsize=(15,5))
    plt.tight_layout()
    plot_aurocs(train_history, title='Train - AUROC Scores', axis=axes[0])
    plot_aurocs(valid_history, title='Valid - AUROC Scores', axis=axes[1])

# Cell
def plot_fit_results(history, labels):
    '''All plots after fit - ROC curves, losses and AUROCs'''
    h = history
    train_rocs, valid_rocs = MultiLabelROC(h.y_train, h.yhat_train, labels), MultiLabelROC(h.y_valid, h.yhat_valid, labels)
    plot_train_valid_rocs(train_rocs.ROCs, valid_rocs.ROCs, labels, multilabel=True)
    plot_losses(h.train, h.valid)
    plot_train_valid_aurocs(h.train, h.valid)

# Cell
def summarize_prediction(history, labels, plot=True):
    '''Summarize after prediction - plot ROC curves, calculate auroc, optimal threshold and 95% CI for AUROC and return results in `history`'''
    h = history
    test_rocs = MultiLabelROC(h.y_test, h.yhat_test, labels)
    if plot: plot_rocs(test_rocs.ROCs, labels, title='Test ROC curves', multilabel=True)
    print('\nPrediction Summary ...')
    col_names = ['auroc_score', 'optimal_threshold', 'auroc_95_ci']
    rows = []
    for i, label in enumerate(labels):
        row = [test_rocs.ROCs[label].auroc, test_rocs.ROCs[label].optimal_thresh(), auroc_ci(h.y_test[:,i], h.yhat_test[:,i])]
        rows.append(row)
    history.prediction_summary = pd.DataFrame(rows, index=labels, columns=col_names)
    print(history.prediction_summary)
    return history

# Cell
def count_parameters(model, printout=False):
    '''Returns number of parameters in model'''
    total         = sum(p.numel() for p in model.parameters())
    trainable     = sum(p.numel() for p in model.parameters() if p.requires_grad)
    non_trainable = sum(p.numel() for p in model.parameters() if p.requires_grad==False)
    assert total == (trainable+non_trainable)
    print(f'total: {total:,}, trainable: {trainable:,}, non_trainable: {non_trainable:,}')
    return total, trainable, non_trainable