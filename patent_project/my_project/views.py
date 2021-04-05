import requests, json

from django.shortcuts import render
from django.http import HttpResponse

from fuzzywuzzy import fuzz
from fuzzywuzzy import process

import os
from os import path


lens_key = '82QDp7mcObNq6rMT2GG5KLE8VlrwjWL7TZcE0NiEOD0bBobOQqY9'

example_dict = {}
example_dict["009-600-108-934-46X"] = "1. An insulation system for a roof, the insulation system comprising: a plurality of roof sheathing panels that extend upward at an angle away from an eave of the roof toward a ridge of the roof; a plurality of spaced apart structural members having lengths that extend upward at an angle away from the eave toward the ridge without insulation between the roof sheathing panels and the spaced apart structural members, wherein the spaced apart structural members support the roof sheathing panels, wherein the spaced apart structural members each include a top face that faces toward the roof sheathing panel and a bottom face that faces away from the roof sheathing panels; a first insulation material disposed between an adjacent pair of the spaced apart structural members, wherein a length of the first insulation material extends along the lengths of each structural member of the adjacent pair of the spaced apart structural members, wherein the first insulation material has a bottom face that is substantially flush with the bottom faces of the spaced apart structural members, wherein the first insulation material comprises a fibrous material; a second insulation material, wherein a single piece of the second insulation material has a length that extends across the bottom face of each structural member of the adjacent pair of the spaced apart structural members, such that the single piece of the second insulation material covers the bottom face of each structural member of the adjacent pair of the spaced apart structural members and the first insulation material, wherein the second insulation material comprises a fibrous material."
example_dict["053-482-898-165-714"] = "1. A system for passively cooling an interior area within a structure comprising: a membrane assembly covering a portion of the structure, wherein the membrane assembly has an interior side facing the interior area and an exterior side, the membrane assembly defines a plurality of pores."


# Create your views here.
def index(request):
    return HttpResponse("homepage")

def patent_comp(request, id_list):
    id_list = ["009-600-108-934-46X", "053-482-898-165-714"]
    # response_data = lens_request(id_list)
    # claims_dict = {}
    # for patent in response_data:
    #     patent_id = patent.lens_id
    #     claims_dict[patent_id] = parse_claim_text(string)

    claims_dict = example_dict
    return_string = ""

    ratio = fuzz.token_sort_ratio(id_list[0], id_list[1])
    return_string += f"{str(id_list[0])}, {str(id_list[1])}: {ratio} \n"

    # for key, value in claims_dict:

    
    return HttpResponse(return_string)


def lens_request(id_list):
    url = 'https://api.lens.org/patent/search'
    data_dict = {
                "query": {
                    "terms":  {
                        "lens_id": lens_id
                    }
                },
                "size": 100,
                "include": ["claims"],
                "scroll": "1m",
                "scroll_id": ""
            }
    data = json.dumps(data_dict)
    headers = {'Authorization': '82QDp7mcObNq6rMT2GG5KLE8VlrwjWL7TZcE0NiEOD0bBobOQqY9', 'Content-Type': 'application/json'}
    response = requests.post(url, data=data, headers=headers)
    return response.data

    # if response.status_code != requests.codes.ok:
    #     print(response.status_code)
    # else:
    #     print(response.text)

def parse_claim_text(string):
    claim_index = string.index("claim_text")
    return string[claim_index:]

def cto_request(request, expr, fields):
    url = 'ClinicalTrials.gov/api/query/study_fields?expr={expr}&fields={fields}'
    
    # ClinicalTrials.gov/api/query/study_fields?expr=heart+attack&fields=NCTId,Condition,BriefTitle