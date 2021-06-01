import pandas as pd
import io

def make_author_df(ct_df, lens_s_df, lens_p_df, nih_df):
    '''Sort and filter results for common authors.

    arguments:
    df -- populated dataframe

    '''
    translator = {
        'Clinical Trials': [ct_df, 'Authors', 0, -1],
        'Lens Scholar': [lens_s_df, 'Authors', 0, -1],
        'Lens Patent': [lens_p_df, 'Inventors', 1, 0],
        'Federal NIH': [nih_df, 'PI Names', 0, -1]
        }

    author_dict = populate_dict(translator)
    authors_sort_filt = sort_and_filter(author_dict)
    authors_df = make_authors_df(author_dict, authors_sort_filt)

    return authors_df

def populate_dict(translator):
    '''Creates dictionary mapping authors to work across different databases

    arguments:
    *_df: dataframe with data from the given database
    translator: info specific to each to database, such as author name arrangement, etc.
    
    '''
    author_dict = {}
    for db in translator:
        df, col_name, first, last = translator[db]
        for index, row in df.iterrows():
            if pd.isnull(df.loc[index, col_name]):
                continue
            entry = row[col_name]
            authors = entry.split(',')
            for author in authors:
                names = [n.strip() for n in author.split()]
                try:
                    name = (f'{names[first]} {names[last]}').title()
                except IndexError:
                    continue
                info = row["Title"].title()
                if name in author_dict:
                    if db in author_dict[name]:
                        author_dict[name][db].add(info)
                    else:
                        author_dict[name][db] = {info}
                else:
                    author_dict[name] = {db: {info}}

    return author_dict

def sort_and_filter(author_dict):
    authors_sort_filt = []
    for name in author_dict:
        # categories = len(list(author_dict[name].keys()))
        total = sum([len(list(author_dict[name][key])) for key in author_dict[name]])
        if total > 1:
            # authors_sort_filt.append((categories, total, name))
            authors_sort_filt.append((total, name))
    authors_sort_filt.sort(reverse=True)

    return authors_sort_filt

def make_authors_df(author_dict, authors_sort_filt):
    d = {'Name': [], 'Clinical Trials': [], 'Lens Scholar': [], 'Lens Patent': [], 'Federal NIH': []}
    df = pd.DataFrame(data=d)
    # for _, _, name in authors_sort_filt:
    for _, name in authors_sort_filt:
        row_data = {'Name': name}
        data = author_dict[name]
        for database in data:
            titles = '; '.join(data[database])
            row_data[database] = titles
        
        df = df.append(row_data, ignore_index=True)

    return df

def make_authors_xlsx(authors_df):
    xlsx = io.BytesIO()
    PandasWriter = pd.ExcelWriter(xlsx, engine='xlsxwriter')
    authors_df.to_excel(PandasWriter, sheet_name='authors')
    PandasWriter.save()

    xlsx.seek(0)

    return xlsx