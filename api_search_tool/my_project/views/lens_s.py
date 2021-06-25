import requests, json
import pandas as pd

lens_key = 'JsGWcp0DKnphJq3dA71k7hkS4BVKG8ZC0AGYtWtbZB5slK1D8UTH'
lens_size = 200

def get_lens_s_df(entries):
    if len(entries) == 0:
        return pd.DataFrame()

    response_json = make_lens_s_request(entries)
    lens_df = lens_s_json_to_df(response_json)
    return lens_df

def make_lens_s_request(entries):
    url = 'https://api.lens.org/scholarly/search'

    query = {"must":[]}
    years = {"range": {
                "year_published": {
                    "gte": "2000"}
                }}
    query["must"].append(years)

    field_dict = {'keyword': ["title", "field_of_study", "abstract", "full_text"],
                  'author': ["author.display_name", "full_text"],
                  'institution': ["author.affiliation.name", "full_text"],
                  'sponsor': ["author.affiliation.name", "full_text"]}
    try:
        lensid = entries['lens_id']
        query["must"].append({"terms": {'lens_id': [lensid]}})
    except KeyError:
        for key, val in entries.items():
            try:
                if key == 'keyword':
                    words = [word.strip() for word in val.split(';')]
                    for word in words:
                        query_string = {
                            "query_string": {
                                "query": word,
                                    "fields": field_dict[key],
                                    "default_operator": "or"
                                }
                            }
                        query["must"].append(query_string)
                else:
                    query_string = {
                        "query_string": {
                            "query": val,
                                "fields": field_dict[key],
                                "default_operator": "or"
                            }
                        }
                    query["must"].append(query_string)
            except KeyError:
                continue

    boolean = {"bool": query}
    data_dict = {"query": boolean, 
            "size": lens_size, 
            "include": ["clinical_trials", "authors", "chemicals", "keywords", "title"]}
    data_json = json.dumps(data_dict)

    headers = {'Authorization': lens_key, 'Content-Type': 'application/json'}
    response = requests.post(url, data=data_json, headers=headers)
    if response.status_code != requests.codes.ok:
        return response.status_code
    else:
        return json.loads(response.text)

def lens_s_json_to_df(response_json):
    all_data = response_json['data']
    
    response_fields = ["title", "authors", "chemicals", "keywords", "abstract"]
    cols = ["Title", "Institution", "Authors", "Interventions", "Keywords", "Summary"]

    entries = []
    for entry in all_data:
        entry_dict = {col: "" for col in cols}
        for field in response_fields:
            try:
                data = entry[field]
            except:
                continue
            keys, values = clean_lens_data(field, data)
            for key, val in zip(keys, values):
                entry_dict[key] = val

        entries.append(entry_dict)

    df = pd.DataFrame(entries)
    return df

def clean_lens_data(field, data):
    keys = []
    values = []
    names = {'title': 'Title', 'keywords': 'Keywords', 'chemicals': 'Interventions', 'abstract': 'Summary'}

    if field == "authors":
        first_names = [author['first_name'] if 'first_name' in author else "" for author in data]
        last_names = [author['last_name'] if 'last_name' in author else "" for author in data]
        nested_affs = [[a['name'] for a in author['affiliations']] for author in data if 'affiliations' in author]

        names = [first + " " + last for first, last in zip(first_names, last_names)]
        affs = [name for aff in nested_affs for name in aff]

        keys += ['Authors', 'Institution']
        values += [names, affs]

    else:
        keys.append(names[field])
        if field == 'chemicals':
            data = [chemical['substance_name'] for chemical in data]
        values.append(data)
    
    values = [', '.join(map(str, list(set(val)))) if type(val) != str else val for val in values]

    return keys, values