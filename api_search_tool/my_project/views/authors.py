import pandas as pd
import io

def make_author_df(ct_df, lens_s_df, lens_p_df, nih_df):
    '''Sort and filter results for common authors.

    arguments:
    df -- populated dataframe

    '''
    translator = {
        'Clinical Trials': [ct_df, 'Authors', 0, -1],
        # 'Lens Scholar': [lens_s_df, 'Authors', 0, -1],
        # 'Lens Patent': [lens_p_df, 'Inventors', 1, 0],
        'Federal NIH': [nih_df, 'PI Names', 0, -1]
        }

    author_dict = populate_dict(translator)
    authors_sort_filt, db_count_tuples = sort_and_filter(author_dict, translator)
    all_dfs = make_authors_df(author_dict, authors_sort_filt, db_count_tuples)

    return all_dfs

def populate_dict(translator):
    '''Creates dictionary mapping authors to work across different databases

    arguments:
    *_df: dataframe with data from the given database
    translator: info specific to each to database, such as author name arrangement, etc.
    
    '''
    author_dict = {}
    for db in translator:
        df, col_name, first, last = translator[db]
        for index, row in df.iterrows(): # for every publication
            if pd.isnull(df.loc[index, col_name]):
                continue
            entry = row[col_name]
            authors = entry.split(',')
            for author in authors:
                names = [n.strip() for n in author.split()]
                if len(names) < 2:
                    continue
                try:
                    name = (f'{names[first]} {names[last]}').title()
                except IndexError:
                    continue
                info = row["Title"].title()
                if name in author_dict:
                    if db in author_dict[name]:
                        author_dict[name][db].append(info)
                    else:
                        author_dict[name][db] = [info]
                else:
                    author_dict[name] = {db: [info]}

    return author_dict

author_dict = {'Jasmine Wu': {'Clinical Trials': 'fake_trial', 'Lens Scholar': 'fake scholar', 'Federal NIH': 'fake grant'}}

def sort_and_filter(author_dict, translator):
    authors_sort_filt = []
    db_count_tuples = {db: [] for db in translator}
    for name, info in author_dict.items():
        total = sum([len(info[db]) for db in info])
        authors_sort_filt.append((total, name))

        for db in translator:
            if db in info:
                db_count_tuples[db].append((len(info[db]), name)) # (entries in db, name)

    authors_sort_filt.sort(reverse=True)
    for db, list_names in db_count_tuples.items():
        list_names.sort(reverse=True)

    return authors_sort_filt, db_count_tuples


def make_authors_df(author_dict, authors_sort_filt, db_count_tuples):
    all_dfs = {}

    dbs = ['Clinical Trials', 'Lens Scholar', 'Lens Patent', 'Federal NIH']

    d = {'Name': []}
    d.update({db: [] for db in dbs})

    df_titles = pd.DataFrame(data=d)

    df_counts = pd.DataFrame(data=d)
    df_counts['TOTALS'] = []

    for total, name in authors_sort_filt:

        titles_row = {'Name': name}
        counts_row = {'Name': name}
        counts_row.update({db: 0 for db in dbs})

        author_info = author_dict[name]
        for database, title_list in author_info.items():
            title_str = '; '.join(title_list)
            titles_row[database] = title_str

            counts_row[database] = len(title_list)

        counts_row['TOTALS'] = total
        
        df_titles = df_titles.append(titles_row, ignore_index=True)
        df_counts = df_counts.append(counts_row, ignore_index=True)

    all_dfs['authors- titles'] = df_titles
    all_dfs['authors- totals'] = df_counts

    for db, db_list in db_count_tuples.items():
        format = {'Name': [], 'Count': [], 'Titles': []}
        db_df = pd.DataFrame(data=format)
        for total, name in db_list:
            titles = '; '.join(author_dict[name][db])
            row = {'Name': name, 'Count': total, 'Titles': titles}

            db_df = db_df.append(row, ignore_index=True)
        
        all_dfs[f'authors- {db.lower()}'] = db_df

    return all_dfs
