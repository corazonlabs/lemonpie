# AUTOGENERATED! DO NOT EDIT! File to edit: 01_preprocessing_clean.ipynb (unless otherwise specified).

__all__ = ['read_raw_ehrdata', 'split_patients', 'split_ehr_dataset', 'cleanup_pts', 'cleanup_obs', 'cleanup_algs',
           'cleanup_crpls', 'cleanup_meds', 'cleanup_img', 'cleanup_procs', 'cleanup_cnds', 'cleanup_immns',
           'cleanup_dataset', 'extract_ys', 'insert_age', 'clean_raw_ehrdata', 'load_cleaned_ehrdata',
           'load_ehr_vocabcodes']

# Cell
from ..basics import *
from fastai.imports import *

# Cell
def read_raw_ehrdata(path, csv_names = FILENAMES):
    '''Read raw EHR data'''
    dfs = [pd.read_csv(f'{path}/{fname}.csv', low_memory=False) for fname in csv_names]
    return dfs

# Cell
def split_patients(patients, valid_pct=0.2, test_pct=0.2, random_state=1234):
    '''Split the patients dataframe'''
    train_pct = 1 - (valid_pct + test_pct)
    print(f'Splits:: train: {train_pct}, valid: {valid_pct}, test: {test_pct}')
    patients = patients.sample(frac=1, random_state=random_state).reset_index(drop=True)
    return np.split(patients, [int(train_pct*len(patients)), int((train_pct+valid_pct)*len(patients))])

# Cell
def split_ehr_dataset(path, valid_pct=0.2, test_pct=0.2, random_state=1234):
    '''Split EHR dataset into train, valid, test and save'''

    train_dfs, valid_dfs, test_dfs = [],[],[]

    dfs = read_raw_ehrdata(f'{path}/raw_original')
    all_pts = dfs[0]
    all_pts.rename(str.lower, axis='columns', inplace=True)
    train_pt, valid_pt, test_pt = split_patients(dfs[0], valid_pct, test_pct, random_state)
    train_dfs.append(train_pt)
    valid_dfs.append(valid_pt)
    test_dfs.append(test_pt)
    print(f'Split {FILENAMES[0]} into:: Train: {len(train_pt)}, Valid: {len(valid_pt)}, Test: {len(test_pt)} -- Total before split: {len(dfs[0])}')

    for df, name in zip(dfs[1:], FILENAMES[1:]):
        df = df.set_index('PATIENT')
        df_train = df.loc[df.index.intersection(train_pt['id']).unique()]
        df_valid = df.loc[df.index.intersection(valid_pt['id']).unique()]
        df_test = df.loc[df.index.intersection(test_pt['id']).unique()]
        assert len(df) == len(df_train)+len(df_valid)+len(df_test),f'Split failed {name}: {len(df)} != {len(df_train)}+{len(df_valid)}+{len(df_test)}'
        train_dfs.append(df_train.reset_index())
        valid_dfs.append(df_valid.reset_index())
        test_dfs.append(df_test.reset_index())


    for split in ['train', 'valid', 'test']:
        d = Path(f'{path}/raw_split/{split}')
        d.mkdir(parents=True, exist_ok=True)

        if split == 'train':
            for df, name in zip(train_dfs, FILENAMES):
                df.to_csv(f'{d}/{name}.csv', index=False)
            print(f'Saved train data to {d}')

        if split == 'valid':
            for df, name in zip(valid_dfs, FILENAMES):
                df.to_csv(f'{d}/{name}.csv', index=False)
            print(f'Saved valid data to {d}')

        if split == 'test':
            for df, name in zip(test_dfs, FILENAMES):
                df.to_csv(f'{d}/{name}.csv', index=False)
            print(f'Saved test data to {d}')

# Cell
def cleanup_pts(pts, is_train, today=None):
    '''Clean patients df'''

    pts.rename(str.lower, axis='columns', inplace=True)
    pts = pts.loc[:, ['id', 'birthdate', 'marital', 'race', 'ethnicity', 'gender', 'birthplace', 'city', 'state', 'zip']]
    pts.rename(columns={"id":"patient"}, inplace=True)
    pts = pts.astype({'birthdate':'datetime64'})
    pts['zip'] = pts['zip'].fillna(0.0).astype(int)
    if today == None: today = pd.Timestamp.today()
    else            : today = pd.to_datetime(today)
    pts['age_now_days'] = pts['birthdate'].apply(lambda bday: (today-bday).days)

    pts.fillna('xxxnan', inplace=True)
    if is_train: pt_codes = pts.drop(columns=['patient'], inplace=False)
    pts.set_index('patient', inplace=True)
    pt_demographics = pts
    patients = pts.loc[:,['birthdate']]

    return [patients, pt_demographics, pt_codes] if is_train else [patients, pt_demographics]

# Cell
def cleanup_obs(obs, is_train):
    '''Clean observations df'''

    obs.rename(str.lower, axis='columns', inplace=True)
    obs.units.fillna('xxxnan', inplace=True)
    obs.dropna(subset=['value'], inplace=True)

    obs.rename(columns={"code":"orig_code", "description":"desc"}, inplace=True)
    obs['code'] = obs['orig_code'].str.cat(obs[['value', 'units', 'type']].astype(str), sep='||')

    if is_train: obs_codes = obs.loc[:, ['orig_code', 'desc', 'value', 'units', 'type']]

    obs = obs.loc[:, ['patient', 'date', 'code']]
    obs = obs.astype({'date':'datetime64'})
    obs.set_index('patient', inplace=True)

    return [obs, obs_codes] if is_train else [obs]

# Cell
def cleanup_algs(allergies, is_train):
    '''Clean allergies df'''

    allergies.rename(str.lower, axis='columns', inplace=True)
    allergies.drop(columns=['encounter'], inplace=True)

    stops = pd.DataFrame(allergies.loc[allergies['stop'].notnull(),:])
    allergies['code'] = allergies['code'].apply(lambda x: f'{str(x)}||START')
    stops['code'] = stops['code'].apply(lambda x: f'{str(x)}||STOP')
    allergies.drop(columns=['stop'], inplace=True)
    stops.drop(columns=['start'], inplace=True)
    allergies.rename(columns={"start":"date", "description":"desc"}, inplace=True)
    stops.rename(columns={"stop":"date", "description":"desc"}, inplace=True)
    allergies = allergies.append(stops, ignore_index=True)

    if is_train: alg_codes = allergies.loc[:, ['code', 'desc']]

    allergies.drop(columns=['desc'], inplace=True)
    allergies = allergies.astype({'date':'datetime64'})
    allergies.set_index('patient', inplace=True)
    return [allergies, alg_codes] if is_train else [allergies]

# Cell
def cleanup_crpls(careplans, is_train):
    '''Clean careplans df'''

    careplans.rename(str.lower, axis='columns', inplace=True)
    careplans = careplans.loc[:, ['start', 'stop', 'patient', 'code', 'description']]

    stops = pd.DataFrame(careplans.loc[careplans['stop'].notnull(),:])
    careplans['code'] = careplans['code'].apply(lambda x: f'{str(x)}||START')
    stops['code'] = stops['code'].apply(lambda x: f'{str(x)}||STOP')
    careplans.drop(columns=['stop'], inplace=True)
    stops.drop(columns=['start'], inplace=True)
    careplans.rename(columns={"start":"date", "description":"desc"}, inplace=True)
    stops.rename(columns={"stop":"date", "description":"desc"}, inplace=True)
    careplans = careplans.append(stops, ignore_index=True)

    if is_train: crpl_codes = careplans.loc[:, ['code', 'desc']]

    careplans.drop(columns=['desc'], inplace=True)
    careplans = careplans.astype({'date':'datetime64'})
    careplans.set_index('patient', inplace=True)
    return [careplans, crpl_codes] if is_train else [careplans]

# Cell
def cleanup_meds(medications, is_train):
    '''Clean `medications` df'''

    medications.rename(str.lower, axis='columns', inplace=True)
    medications = medications.loc[:, ['start', 'stop', 'patient', 'code', 'description']]

    stops = pd.DataFrame(medications.loc[medications['stop'].notnull(),:])
    medications['code'] = medications['code'].apply(lambda x: f'{str(x)}||START')
    stops['code'] = stops['code'].apply(lambda x: f'{str(x)}||STOP')
    medications.drop(columns=['stop'], inplace=True)
    stops.drop(columns=['start'], inplace=True)
    medications.rename(columns={"start":"date", "description":"desc"}, inplace=True)
    stops.rename(columns={"stop":"date", "description":"desc"}, inplace=True)
    medications = medications.append(stops, ignore_index=True)

    if is_train: med_codes = medications.loc[:, ['code', 'desc']]

    medications.drop(columns=['desc'], inplace=True)
    medications = medications.astype({'date':'datetime64'})
    medications.set_index('patient', inplace=True)
    return [medications, med_codes] if is_train else [medications]

# Cell
def cleanup_img(imaging_studies, is_train):
    '''Clean `imaging` df'''

    imaging_studies.rename(str.lower, axis='columns', inplace=True)
    imaging_studies.rename(columns={"bodysite_code":"code", "bodysite_description":"desc"}, inplace=True)
    if is_train: img_codes = imaging_studies.loc[:, ['code', 'desc']]

    imaging_studies = imaging_studies.loc[:, ['patient', 'date', 'code']]
    imaging_studies = imaging_studies.astype({'date':'datetime64'})
    imaging_studies.set_index('patient', inplace=True)
    return [imaging_studies, img_codes] if is_train else [imaging_studies]

# Cell
def cleanup_procs(procedures, is_train):
    '''Clean `procedures` df'''

    procedures.rename(str.lower, axis='columns', inplace=True)
    procedures.rename(columns={"description":"desc"}, inplace=True)
    if is_train: proc_codes = procedures.loc[:, ['code', 'desc']]

    procedures = procedures.loc[:, ['patient', 'date', 'code']]
    procedures = procedures.astype({'date':'datetime64'})
    procedures.set_index('patient', inplace=True)
    return [procedures, proc_codes] if is_train else [procedures]

# Cell
def cleanup_cnds(conditions, is_train):
    '''Clean `conditions` df'''

    conditions.rename(str.lower, axis='columns', inplace=True)
    conditions.drop(columns=['encounter'], inplace=True)
    stops = pd.DataFrame(conditions.loc[conditions['stop'].notnull(),:])
    conditions['code'] = conditions['code'].apply(lambda x: f'{str(x)}||START')
    stops['code'] = stops['code'].apply(lambda x: f'{str(x)}||STOP')
    conditions.drop(columns=['stop'], inplace=True)
    stops.drop(columns=['start'], inplace=True)
    conditions.rename(columns={"start":"date", "description":"desc"}, inplace=True)
    stops.rename(columns={"stop":"date","description":"desc"}, inplace=True)
    conditions = conditions.append(stops, ignore_index=True)

    if is_train: cnd_codes = conditions.loc[:, ['code', 'desc']]

    conditions.drop(columns=['desc'], inplace=True)
    conditions = conditions.astype({'date':'datetime64'})
    conditions.set_index('patient', inplace=True)
    return [conditions, cnd_codes] if is_train else [conditions]

# Cell
def cleanup_immns(immunizations, is_train):
    '''Clean `immunizations` df'''

    immunizations.rename(str.lower, axis='columns', inplace=True)
    immunizations.rename(columns={"description":"desc"}, inplace=True)
    if is_train: imm_codes = immunizations.loc[:, ['code', 'desc']]

    immunizations = immunizations.loc[:, ['patient', 'date', 'code']]
    immunizations = immunizations.astype({'date':'datetime64'})
    immunizations.set_index('patient', inplace=True)
    return [immunizations, imm_codes] if is_train else [immunizations]

# Cell
def cleanup_dataset(path, is_train, today=None):
    '''Clean all dfs in a split'''
    dfs = read_raw_ehrdata(path)

    pt_data   = cleanup_pts(dfs[0],   is_train, today)
    obs_data  = cleanup_obs(dfs[1],   is_train)
    alg_data  = cleanup_algs(dfs[2],  is_train)
    crpl_data = cleanup_crpls(dfs[3], is_train)
    med_data  = cleanup_meds(dfs[4],  is_train)
    img_data  = cleanup_img(dfs[5],   is_train)
    proc_data = cleanup_procs(dfs[6], is_train)
    cnd_data  = cleanup_cnds(dfs[7],  is_train)
    imm_data  = cleanup_immns(dfs[8], is_train)

    data_tables = [pt_data[0], pt_data[1], obs_data[0], alg_data[0], crpl_data[0], med_data[0], img_data[0], proc_data[0], cnd_data[0], imm_data[0]]
    if is_train:
        code_tables = [pt_data[2], obs_data[1], alg_data[1], crpl_data[1], med_data[1], img_data[1], proc_data[1], cnd_data[1], imm_data[1]]

    return (data_tables, code_tables) if is_train else (data_tables)

# Cell
def extract_ys(patients, conditions, cnd_dict):
    '''Extract labels from conditions df and add them to patients df with age'''
    for key in cnd_dict.keys():
        patients = patients.merge(conditions[conditions.code==f'{cnd_dict[key]}||START'], how='left', left_index=True, right_index=True)
        patients[f'{key}'] = patients.code.notna()
        patients[f'{key}_age'] = ((patients.date - patients.birthdate)//np.timedelta64(1,'Y'))
        patients = patients.drop(columns=['date','code'])
    return patients

# Cell
def insert_age(df, pts_df):
    '''Insert age in years and months into each of the rec dfs'''
    df = df.merge(pts_df, left_index=True, right_index=True)
    df['age']        = (df['date'] - df['birthdate'])//np.timedelta64(1,'Y')
    df['age_months'] = (df['date'] - df['birthdate'])//np.timedelta64(1,'M')
    return df.drop(columns=['date','birthdate'])

# Cell
def clean_raw_ehrdata(path, valid_pct, test_pct, conditions_dict, today=None):
    '''Split, clean, preprocess & save raw EHR data'''
    split_ehr_dataset(path, valid_pct, test_pct)

    for split in ['train', 'valid', 'test']:
        split_path = f'{path}/raw_split/{split}'
        if split == 'train': data_tables, code_tables = cleanup_dataset(split_path, is_train=True, today=today)
        else               : data_tables = cleanup_dataset(split_path, is_train=False)
        patients, conditions, rec_tables = data_tables[0], data_tables[8], data_tables[2:]
        patients = extract_ys(patients, conditions, conditions_dict)
        rec_dfs = [insert_age(rec_df, pd.DataFrame(patients.birthdate)) for rec_df in rec_tables]

        cleaned_dir = Path(f'{path}/cleaned/{split}')
        cleaned_dir.mkdir(parents=True, exist_ok=True)

        for rec_df,name in zip(rec_dfs,FILENAMES[1:]):
            rec_df.to_csv(f'{cleaned_dir}/{name}.csv')
        patients.reset_index(inplace=True)
        patients.to_csv(f'{cleaned_dir}/patients.csv', index_label='indx')
        data_tables[1].to_csv(f'{cleaned_dir}/patient_demographics.csv')
        print(f'Saved cleaned "{split}" data to {cleaned_dir}')

        if split == 'train':
            codes_dir = Path(f'{cleaned_dir}/codes')
            codes_dir.mkdir(parents=True, exist_ok=True)
            for code_df,name in zip(code_tables, FILENAMES):
                code_df.to_csv(f'{codes_dir}/code_{name}.csv', index_label='indx')
            print(f'Saved vocab code tables to {codes_dir}')

# Cell
def load_cleaned_ehrdata(path):
    '''Load cleaned, age-filtered EHR data'''

    csv_names = FILENAMES.copy()
    csv_names.insert(1,'patient_demographics')

    train_dfs = [pd.read_csv(f'{path}/cleaned/train/{fname}.csv', low_memory=False, index_col=0) for fname in csv_names]
    valid_dfs = [pd.read_csv(f'{path}/cleaned/valid/{fname}.csv', low_memory=False, index_col=0) for fname in csv_names]
    test_dfs  = [pd.read_csv(f'{path}/cleaned/test/{fname}.csv', low_memory=False, index_col=0) for fname in csv_names]

    return train_dfs, valid_dfs, test_dfs

# Cell
def load_ehr_vocabcodes(path):
    '''Load codes for vocabs'''

    code_dfs = [pd.read_csv(f'{path}/cleaned/train/codes/code_{fname}.csv', low_memory=False, na_filter=False, index_col=0) for fname in FILENAMES]

    return code_dfs