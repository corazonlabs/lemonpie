# AUTOGENERATED! DO NOT EDIT! File to edit: 02_preprocessing_vocab.ipynb (unless otherwise specified).

__all__ = ['EhrVocab', 'ObsVocab', 'EhrVocabList', 'get_all_emb_dims']

# Cell
from ..setup import *
from .clean import *
from fastai.imports import *
from datetime import date

# Cell
class EhrVocab():
    '''Vocab class for most EHR datatypes'''
    def __init__(self, itoc, ctoi, ctod=None):
        self.itoc = itoc
        self.ctoi = ctoi
        if ctod is not None: self.ctod = ctod
        self.vocab_size = len(self.itoc)

    @classmethod
    def create(cls, codes_df):
        '''Create vocab object (itoc, ctoi and maybe ctod) from the codes df'''
        desc_exists = 'desc' in codes_df.columns
        codes_df = codes_df.astype({'code':'str'})
        itoc = list(codes_df.code.unique())  #old --> list(set(codes_df.code))
        itoc.insert(0,'xxnone')
        itoc.insert(1,'xxunk')

        ctoi = {code: i for i, code in enumerate(itoc)}

        if desc_exists:
            codes_df.set_index('code', inplace=True)
            ctod = {}
            ctod[itoc[0]] = "Nothing recorded"
            ctod[itoc[1]] = "Unknown"
            for code in itoc[2:]:
                ctod[code] = set(codes_df.loc[code].desc)

        return cls(itoc, ctoi, ctod) if desc_exists else cls(itoc, ctoi)

    def get_emb_dims(self, αd=0.5736):
        '''Get embedding dimensions'''
        return self.vocab_size, round(6* αd * (self.vocab_size**0.25))

    def numericalize(self, codes, log_excep=LOG_NUMERICALIZE_EXCEP, log_dir=LOG_STORE):
        '''Lookup and return indices for codes'''

        if log_excep:
            today = date.today().strftime("%Y-%m-%d")
            if not os.path.isdir(log_dir): os.mkdir(log_dir)
            logfile = f'{log_dir}/{today}_numericalize_exceptions.log'

        res = []
        try:
            res = [self.ctoi[str(code)] for code in codes] #no big performance benefit
        except KeyError:
            for code in codes:
                try:
                    res.append(self.ctoi[str(code)])
                except KeyError:
                    res.append(self.ctoi['xxunk'])
                    if log_excep:
                        with open(logfile, 'a') as log:
                            log.write(f'\ncode: {code}')

        return res

    def textify(self, indxs):
        '''Lookup and return descriptions for codes'''
        if hasattr(self, 'ctod'):
            res = [ (self.itoc[i], self.ctod[self.itoc[i]]) for i in indxs ]
        else:
            res = [ (self.itoc[i]) for i in indxs ]
        return res

# Cell
class ObsVocab (EhrVocab):
    '''Special Vocab class for Observation codes'''
    def __init__(self, vocab_df):
        self.vocab_df = vocab_df
        self.vocab_size = len(vocab_df)

    def numericalize(self, codes, log_excep=LOG_NUMERICALIZE_EXCEP, log_dir=LOG_STORE):
        '''Numericalize observation codes (return indices for codes)'''

        if log_excep:
            today = date.today().strftime("%Y-%m-%d")
            if not os.path.isdir(log_dir): os.mkdir(log_dir)
            logfile = f'{log_dir}/{today}_numericalize_exceptions.log'

        indxs = []
        for code in codes:
            if code in ['xxnone','xxunk']: indxs.extend(self.vocab_df[(self.vocab_df['code'] == code)].index.tolist())
            else:
                c,v,u,t = code.split('||')
                if t == 'numeric':
                    filt_df = self.vocab_df[(self.vocab_df['code'] == c) & (self.vocab_df['units'] == u) & (self.vocab_df['type'] == t)]
                    res = filt_df.iloc[(filt_df.value - float(v)).abs().argsort()[:1]].index.tolist()
                else:
                    res = self.vocab_df[(self.vocab_df['code'] == c) & (self.vocab_df['value'] == v) & \
                                               (self.vocab_df['units'] == u) & (self.vocab_df['type'] == t)].index.tolist()
                if len(res) == 0:
                    indxs.extend(self.vocab_df[(self.vocab_df['code'] == 'xxunk')].index.tolist())
                    if log_excep:
                        with open(logfile, 'a') as log:
                            log.write(f'\ncode in ObsVocab: {code}')
                else            : indxs.extend(res)

        assert len(codes) == len(indxs), "Possible bug, not all codes being numericalized"
        return indxs

    def textify(self, indxs):
        '''Textify observation codes (returns codes and descriptions)'''
        txts = []
        for i in indxs:
            c,d,v,u,t = self.vocab_df.iloc[i]
            if i == 0: txts.append((c, d))
            else:      txts.append((f'{c}||{v}||{u}||{t}', d))
        assert len(indxs) == len(txts), "Possible bug, not all indxs being textified"
        return txts

    @classmethod
    def create(cls, obs_codes, num_buckets=5):
        '''Create vocab object from observation codes'''
        numerics = pd.DataFrame(obs_codes.loc[obs_codes['type'] == 'numeric',:])
        texts = pd.DataFrame(obs_codes.loc[obs_codes['type'] == 'text',:])
        numerics = numerics.astype({'value':'float'}, copy=False)
        vocab_rows = []

        for code in numerics.orig_code.unique():
            this_code = numerics.loc[numerics['orig_code'] == code]
            for unit in this_code.units.unique():
                this_unit = this_code.loc[this_code['units'] == unit]
                for val in np.linspace(this_unit.value.min(), this_unit.value.max(), num=num_buckets):
                    vocab_rows.append([code,this_unit.desc.iloc[0],val,unit,'numeric'])

        for code in texts.orig_code.unique():
            this_code = texts.loc[texts['orig_code'] == code]
            for unit in this_code.units.unique():
                this_unit = this_code.loc[this_code['units'] == unit]
                for val in this_unit.value.unique():
                    vocab_rows.append([code,this_unit.desc.iloc[0],val,unit,'text'])

        vocab_rows.insert(0, ['xxnone','Nothing recorded','xxnone','xxnone','xxnone'])
        vocab_rows.insert(1, ['xxunk','Unknown','xxunk','xxunk','xxunk'])
        obs_vocab = pd.DataFrame(data=vocab_rows, columns=['code','desc','value','units','type'])
        assert obs_codes.orig_code.nunique() == obs_vocab.code.nunique()-2, "Possible bug, obs_code nuniques don't match"
        return cls(obs_vocab)

# Cell
class EhrVocabList:
    '''Class to create and hold all vocab objects for an entire dataset'''
    def __init__(self, demographics_vocabs, records_vocabs, age_mean, age_std, path):
        self.demographics_vocabs, self.records_vocabs, self.path = demographics_vocabs, records_vocabs, path
        self.age_mean, self.age_std = age_mean, age_std

    @classmethod
    def create(cls, path, num_buckets=5):
        '''Read all code dfs from the dataset path and create all vocab objects'''
        demographics_vocabs, records_vocabs = [], []
        code_dfs = load_ehr_vocabcodes(path)

        def _get_demographics_codes(pt_codes):
            code_dfs = []
            code_dfs.extend([pd.DataFrame(range(1, 32, 1), columns=['code'])]) #31 days
            code_dfs.extend([pd.DataFrame(range(1, 13, 1), columns=['code'])]) #12 months
            code_dfs.extend([pd.DataFrame(range(1900, pd.Timestamp.today().year + 1, 1), columns=['code'])]) #years 1900 to now
            code_dfs.extend([pd.DataFrame(pt_codes.marital.dropna().unique(), columns=['code'])])
            code_dfs.extend([pd.DataFrame(pt_codes.race.dropna().unique(), columns=['code'])])
            code_dfs.extend([pd.DataFrame(pt_codes.ethnicity.dropna().unique(), columns=['code'])])
            code_dfs.extend([pd.DataFrame(pt_codes.gender.dropna().unique(), columns=['code'])])
            code_dfs.extend([pd.DataFrame(pt_codes.birthplace.dropna().unique(), columns=['code'])])
            code_dfs.extend([pd.DataFrame(pt_codes.city.dropna().unique(), columns=['code'])])
            code_dfs.extend([pd.DataFrame(pt_codes.state.dropna().unique(), columns=['code'])])
            code_dfs.extend([pd.DataFrame(pt_codes.zip.dropna().unique(), columns=['code'])])
            age_mean, age_std = pt_codes.age_now_days.mean(), pt_codes.age_now_days.std()
            return code_dfs, age_mean, age_std

        demographics_codes, age_mean, age_std = _get_demographics_codes(code_dfs[0])
        demographics_vocabs.extend([EhrVocab.create(codes_df) for codes_df in demographics_codes])
        records_vocabs.extend([ObsVocab.create(code_dfs[1], num_buckets)])
        records_vocabs.extend([EhrVocab.create(codes_df) for codes_df in code_dfs[2:]])
        return cls(demographics_vocabs, records_vocabs, age_mean, age_std, path)

    def save(self):
        '''Save vocablist (containing all vocab objects for the dataset)'''
        pckl_dir = Path(f'{self.path}/processed')
        pckl_dir.mkdir(parents=True, exist_ok=True)
        pckl_f = open(f'{pckl_dir}/vocabs.vocablist', 'wb')
        pickle.dump(self, pckl_f)
        pckl_f.close()
        print(f'Saved vocab lists to {pckl_dir}')

    @classmethod
    def load(cls, path):
        '''Load previously created vocablist object (containing all vocab objects for the dataset)'''
        infile = open(f'{path}/processed/vocabs.vocablist','rb')
        ehrVocabList = pickle.load(infile)
        infile.close()
        return ehrVocabList

# Cell
def get_all_emb_dims(EhrVocabList, αd=0.5736):
    '''Get embedding dimensions for all vocab objects of the dataset'''
    demographics_dims = [vocab.get_emb_dims(αd) for vocab in EhrVocabList.demographics_vocabs]
    recs_dims          = [vocab.get_emb_dims(αd) for vocab in EhrVocabList.records_vocabs]

#     emb_dims_list = [vocab.get_emb_dims() for vocab in vocabs_list]
    demographics_dims_width = recs_dims_width = 0
    for emb_dim in demographics_dims:
        demographics_dims_width += emb_dim[1]
    for emb_dim in recs_dims:
        recs_dims_width += emb_dim[1]

    return demographics_dims, recs_dims, demographics_dims_width, recs_dims_width