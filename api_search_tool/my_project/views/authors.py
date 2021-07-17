import pandas as pd
import io


def make_author_df(ct_df, lens_s_df, lens_p_df, nih_df):
    '''Sort and filter results for common authors.

    arguments:
        df -- populated dataframe

    returns:
        dictionary in format {title: dataframe} that contains analysis on author frequency

    '''
    translator = {
        'Clinical Trials': [ct_df, 'Authors', 0, -1],
        # 'Lens Scholar': [lens_s_df, 'Authors', 0, -1],
        # 'Lens Patent': [lens_p_df, 'Inventors', 1, 0],
        'Federal NIH': [nih_df, 'PI Names', 0, -1]
    }

    author_dict = make_author_dict(translator)
    authors_sort_filt, db_count_tuples = sort_and_filter(
        author_dict, translator)
    all_dfs = make_authors_df(translator, author_dict,
                              authors_sort_filt, db_count_tuples)

    return all_dfs


def make_author_dict(translator):
    '''Creates dictionary mapping authors to work across different databases

    arguments:
        translator: info specific to each to database, such as author name arrangement, etc.

    returns: 
        author_dict = {
            Name1: {
                Database1: [Title1, Title2, ...], 
                Database2: [Title3, Title4, ...],
                ...
            }, 
            Name2: {
                Database1: [Title1, Title2, ...], 
                Database2: [Title3, Title4, ...],
                ...
            }, 
            ...
        }

    '''

    author_dict = {}

    for db in translator:

        df, author_column, index_firstn, index_lastn = translator[db]

        for index, row in df.iterrows():  # for every trial/publication/patent/grant

            if pd.isnull(df.loc[index, author_column]):  # if no name given
                continue

            entry = row[author_column]
            authors = entry.split(',')
            title = row["Title"].title()

            for author in authors:
                names = [n.strip() for n in author.split()]

                if len(names) < 2:  # if only one 'name' (usually its just 'md')
                    continue

                try:
                    # format and capitalize name
                    name = (
                        f'{names[index_firstn]} {names[index_lastn]}').title()
                except IndexError:
                    continue

                if name in author_dict:

                    # name and database exists
                    if db in author_dict[name]:
                        author_dict[name][db].append(title)

                    # name exists
                    else:
                        author_dict[name][db] = [title]

                # neither exists
                else:
                    author_dict[name] = {db: [title]}

    return author_dict


def sort_and_filter(author_dict, translator):
    '''Filters through author_dict structure to build sorted dictionary and list

    arguments:
        author_dict: dictionary of author's works across databases. from make_author_dict()
        translator: info specific to each to database, such as author name arrangement, etc.

    returns:
        authors_sort_filt = [(Total appearances of author, author name), ...] sorted in reverse order
        db_count_tuples = {
            Database1: [(Total appearances of author, author name), ...] sorted in reverse order, 
            Database2: [(Total appearances of author, author name), ...] sorted in reverse order, 
            ...
        }

    '''

    authors_sort_filt = []
    db_count_tuples = {db: [] for db in translator}

    for name, author_info in author_dict.items():
        # total appearances across all dbs
        total = sum([len(author_info[db]) for db in author_info])
        authors_sort_filt.append((total, name))

        for db in translator:
            if db in author_info:
                db_count_tuples[db].append(
                    (len(author_info[db]), name))  # (entries in db, name)

    # sort all lists of tuples in reverse order
    authors_sort_filt.sort(reverse=True)
    for db, list_names in db_count_tuples.items():
        list_names.sort(reverse=True)

    return authors_sort_filt, db_count_tuples


def make_authors_df(translator, author_dict, authors_sort_filt, db_count_tuples):
    '''Using data structures, creates all dataframes relevant to authors

    arguments:
        translator: info specific to each to database, such as author name arrangement, etc.
        author_dict: dictionary of author's works across databases. from make_author_dict()
        authors_sort_filt: list of authors reverse sorted based on total appearances
        db_count_tuples: similar to authors_sort_filt but broken down for each database

    returns:
        all_dfs = {Description: Dataframe, ...}

    '''
    all_dfs = {}

    dbs = list(translator.keys())

    d = {'Name': []}
    d.update({db: [] for db in dbs})

    # df_titles and df_counts are almost identical-
    # titles has actual titles and counts just has the number
    df_titles = pd.DataFrame(data=d) # {'Name': [], 'Databases': []}

    df_counts = pd.DataFrame(data=d) # {'Name': [], 'Databases': [], 'TOTALS': []}
    df_counts['TOTALS'] = []

    for total, name in authors_sort_filt:

        titles_row = {'Name': name}

        counts_row = {'Name': name}
        counts_row.update({db: 0 for db in dbs})

        author_info = author_dict[name]
        for database, title_list in author_info.items(): # populate with titles and counts

            title_str = '; '.join(title_list)
            titles_row[database] = title_str

            counts_row[database] = len(title_list)

        counts_row['TOTALS'] = total

        df_titles = df_titles.append(titles_row, ignore_index=True)
        df_counts = df_counts.append(counts_row, ignore_index=True)

    all_dfs['authors- titles'] = df_titles
    all_dfs['authors- totals'] = df_counts

    # "rank" sheet for each database
    for db, db_list in db_count_tuples.items():

        format = {'Name': [], 'Count': [], 'Titles': []}
        db_df = pd.DataFrame(data=format)

        for total, name in db_list:

            titles = '; '.join(author_dict[name][db])

            row = {'Name': name, 'Count': total, 'Titles': titles}
            db_df = db_df.append(row, ignore_index=True)

        all_dfs[f'authors- {db.lower()}'] = db_df # give it a name and add to all dfs dict

    return all_dfs
