import requests, json
import pandas as pd

# NIH
def get_nih_df(entries):
    try:
        del entries['lens_id']
    except KeyError:
        pass

    if len(entries) == 0:
        return pd.DataFrame()
        
    response_json = make_nih_request(entries)
    nih_df = nih_list_to_df(response_json)
    return nih_df

def make_nih_request(entries):
    url = 'https://api.federalreporter.nih.gov/v1/Projects/search'

    query_string = '?query='
    queries = []

    if 'keyword' in entries:
        keywords = [word.strip() for word in entries['keyword'].split(';')]
        for word in keywords:
            queries.append(f'text%3A{word}%24textFields%3Aterms')

    translator = {'author': 'piName', 'institution': 'orgName', 'state': 'orgState'}
    for key, val in entries.items():
        try:
            new_val = val.replace(' ', '%20')
            queries.append(f'{translator[key]}%3A{new_val}')
        except KeyError:
            continue

    fiscal_years = ','.join(str(x) for x in range(2000, 2022))
    queries.append(f'fy:{fiscal_years}')

    query_string += '%24'.join(queries)

    complete_url = url + query_string
    response = requests.get(complete_url).json()

    all_items = []
    size = response['totalCount']
    items = response['items']
    all_items += items

    iterations = int(size/50)
    for i in range(iterations):
        new_url = complete_url + f'&offset={(i + 1)*50 + 1}'
        response = requests.get(new_url).json()
        items = response['items']
        all_items += items

    return all_items

def nih_list_to_df(all_items):
    rows = []
    columns = ['title', 'fy', 'smApplId', 'piNames', 'orgName', 'orgLoc', 'keywords', 'abstract']
    new_cols = {'title': 'Title', 'fy': 'Year', 'smApplId': 'smApplId', 'piNames': 'PI Names', 'orgName': 'Organization', 'orgLoc': 'Location', 'keywords': 'Keywords', 'abstract': 'Summary'}
    for result in all_items:
        row = {}
        for old_name, new_name in new_cols.items():
            try:
                row[new_name] = result[old_name]
            except KeyError:
                row[new_name] = None
        
        all_people = []
        people1 = result['contactPi']
        people2 = result['otherPis']
        for people in [people1, people2]:
            if people is None:
                continue
            cleaned = people.strip(' ;')
            for person in cleaned.split(';'):
                name = person.split(',')
                name = [n.strip() for n in name]
                all_people.append(f'{name[1]} {name[0]}')
            
        row['PI Names'] = ', '.join(all_people)

        row['Location'] = f"{result['orgCity']}, {result['orgState']}"
        
        all_terms = set()
        if result['terms'] is not None:
            terms = result['terms'].split(';')
            terms = set([t.strip() for t in terms])
            all_terms.update(terms)
        all_terms = [term for term in list(all_terms) if len(term) > 0]

        terms_string = ", ".join(all_terms)
        row['Keywords'] = terms_string

        rows.append(row)

    df = pd.DataFrame.from_dict(rows)
    return df