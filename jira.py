import credentials

import requests
import json

from types import SimpleNamespace

import logging
log = logging.getLogger(__name__)

PROJECT_TYPE = 'com.pyxis.greenhopper.jira:gh-simplified-scrum-classic'

def searchUser(query):
    log.debug(f'Searching users with "{query}"...')

    resp = requests.get(f'{credentials.INSTANCE}/rest/api/3/user/search?query={query}', auth=(credentials.USER, credentials.TOKEN), headers={'Content-Type':'application/json'})
    resp.raise_for_status()

    return resp.json()

def getIssueTypeSchemeForProject(projectId): 
    log.debug(f'Getting Issue Type Scheme for project "{projectId}"...')

    resp = requests.get(f'{credentials.INSTANCE}/rest/api/3/issuetypescheme/project?projectId={projectId}', auth=(credentials.USER, credentials.TOKEN), headers={'Content-Type':'application/json'})
    resp.raise_for_status()
    
    result = json.loads(resp.text, object_hook=lambda d: SimpleNamespace(**d))
    if len(result.values) > 1:
        raise Exception('Multiple issue type schemes found for the same project!')

    return result.values[0].issueTypeScheme

def getIssueTypeSchemeItems(issueTypeSchemeId):
    log.debug(f'Getting Items for Issue Type Scheme "{issueTypeSchemeId}" ...')

    resp = requests.get(f'{credentials.INSTANCE}/rest/api/3/issuetypescheme/mapping?issueTypeSchemeId={issueTypeSchemeId}', auth=(credentials.USER, credentials.TOKEN), headers={'Content-Type':'application/json'})
    resp.raise_for_status()
    
    result = json.loads(resp.text, object_hook=lambda d: SimpleNamespace(**d))
    if result.isLast == False:
        raise Exception('Too Many Issue Types!')

    return result.values


def addIssueTypeSchemeItems(issueTypeSchemeId, issueTypeIds):
    log.debug(f'Adding Items to Issue Type Scheme "{issueTypeSchemeId}" ...')

    data = {
        "issueTypeIds": issueTypeIds
    }

    json_data = json.dumps(data)

    resp = requests.put(f'{credentials.INSTANCE}/rest/api/3/issuetypescheme/{issueTypeSchemeId}/issuetype', auth=(credentials.USER, credentials.TOKEN), data=json_data, headers={'Content-Type':'application/json'})
    resp.raise_for_status()
    
    if len(resp.text) > 0:
        result = json.loads(resp.text, object_hook=lambda d: SimpleNamespace(**d))
    else:
        result = ''

    return result


def getIssueTypes():
    log.debug('Getting Issue Types ...')

    resp = requests.get(f'{credentials.INSTANCE}/rest/api/3/issuetype', auth=(credentials.USER, credentials.TOKEN), headers={'Content-Type':'application/json'})
    resp.raise_for_status()

    return resp.json()

def getIssueTypeProperties(issueTypeId):
    log.debug(f'Getting properties for Issue Type "{issueTypeId}" ...')

    resp = requests.get(f'{credentials.INSTANCE}/rest/api/3/issuetype/{issueTypeId}/properties', auth=(credentials.USER, credentials.TOKEN), headers={'Content-Type':'application/json'})
    resp.raise_for_status()
    
    result = json.loads(resp.text, object_hook=lambda d: SimpleNamespace(**d))

    return result.keys


def createProject(key, name, description, url, accountId):
    log.debug('Creating a Classic Scrum Project...')

    data = {
        "key": key,
        "projectTypeKey": "software",
        "projectTemplateKey": PROJECT_TYPE,
        "name": name,
        "description": description,
        "leadAccountId": accountId,
        "url": url
    }

    json_data = json.dumps(data)

    resp = requests.post(f'{credentials.INSTANCE}/rest/api/3/project', auth=(credentials.USER, credentials.TOKEN), data=json_data, headers={'Content-Type':'application/json'})
    resp.raise_for_status()
    
    result = json.loads(resp.text, object_hook=lambda d: SimpleNamespace(**d))

    return result

def createComponent(name, description, projectKey, accountId):
    log.debug(f'Creating Component "{name}"...')

    data = {
        "isAssigneeTypeValid": False,
        "name": name,
        "description": description,
        "project": projectKey,
        "assigneeType": "PROJECT_LEAD",
        "leadAccountId": accountId
    }

    json_data = json.dumps(data)

    resp = requests.post(f'{credentials.INSTANCE}/rest/api/3/component', auth=(credentials.USER, credentials.TOKEN), data=json_data, headers={'Content-Type':'application/json'})
    resp.raise_for_status()
    
    result = json.loads(resp.text, object_hook=lambda d: SimpleNamespace(**d))

    return result

def createVersion(name, description, projectId,):
    log.debug(f'Creating Version "{name}"...')

    data = {
        "archived": False,
        "released": False,
        "releaseDate": "2022-08-30",
        "name": name,
        "description": description,
        "projectId": projectId
    }

    json_data = json.dumps(data)

    resp = requests.post(f'{credentials.INSTANCE}/rest/api/3/version', auth=(credentials.USER, credentials.TOKEN), data=json_data, headers={'Content-Type':'application/json'})
    resp.raise_for_status()
    
    result = json.loads(resp.text, object_hook=lambda d: SimpleNamespace(**d))

    return result

def getIssueFields():
    log.debug(f'Getting All Issue Fields ...')

    resp = requests.get(f'{credentials.INSTANCE}/rest/api/3/field', auth=(credentials.USER, credentials.TOKEN), headers={'Content-Type':'application/json'})
    resp.raise_for_status()
    
    result = json.loads(resp.text)

    return result

def createIssue(summary, description, projectId, issueTypeName, componentNames, fixVersionNames, epicName, epicLink, epicNameCFId, epicLinkCFId):
    log.debug(f'Creating Issue "{summary}"...')

    components = list(map(lambda componentName: { "name": componentName}, componentNames))
    fixVersions = list(map(lambda versioName: { "name": versioName}, fixVersionNames))

    data = {
        "fields": {
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "text": description,
                                "type": "text"
                            }
                        ]
                    }
                ]
            },
            "project": {
                "id": projectId
            },
            "issuetype": {
                  "name": issueTypeName
            },
            "components": components,
            "fixVersions": fixVersions,
            "labels": [ "default" ]
        }
    }

    if (epicName != None):
        data['fields'][epicNameCFId] = epicName

    if (epicLink != None):
        data['fields'][epicLinkCFId] = epicLink

    json_data = json.dumps(data)

    resp = requests.post(f'{credentials.INSTANCE}/rest/api/3/issue', auth=(credentials.USER, credentials.TOKEN), data=json_data, headers={'Content-Type':'application/json'})
    resp.raise_for_status()

    return resp.json()
    
def createIssueLink(sourceKey, targetKey, issueLinkType):
    log.debug(f'Creating Issue Link "{sourceKey}" -> "{targetKey}" ...')

    data = {
        "outwardIssue": {
            "key": targetKey
        },
        "inwardIssue": {
            "key": sourceKey
        },
        "type": {
            "name": issueLinkType
        }
    }

    json_data = json.dumps(data)

    resp = requests.post(f'{credentials.INSTANCE}/rest/api/3/issueLink', auth=(credentials.USER, credentials.TOKEN), data=json_data, headers={'Content-Type':'application/json'})
    resp.raise_for_status()
   
def AddFieldToDefaultProjectScreen(fieldId, projectKey):
    log.debug(f'Adding field "{fieldId}" to default issue screen of project "{projectKey}" ...')

    # Initialize variables for pagination
    isLast = False
    startAt = 0
    screens = []

    # 1. Get default screen with pagination handling
    while not isLast:
        screens_resp = requests.get(
            f'{credentials.INSTANCE}/rest/api/3/screens?startAt={startAt}', 
            auth=(credentials.USER, credentials.TOKEN), 
            headers={'Content-Type': 'application/json'}
        )
        screens_resp.raise_for_status()

        resp_json = screens_resp.json()
        screens.extend(resp_json['values'])
        isLast = resp_json.get('isLast', True)  # Assume isLast if not provided
        startAt += len(resp_json['values'])

        log.debug(f'Fetched {len(resp_json["values"])} screens')

    # Find the specific screen
    screen = next((s for s in screens if s['name'] == f'{projectKey}: Scrum Default Issue Screen'), None)
    log.debug(f'{screen}')

    if screen is not None:
        # 2. Get tab
        screenId = screen['id']
        tabs_resp = requests.get(
            f'{credentials.INSTANCE}/rest/api/3/screens/{screenId}/tabs', 
            auth=(credentials.USER, credentials.TOKEN), 
            headers={'Content-Type': 'application/json'}
        )
        tabs_resp.raise_for_status()

        tabId = tabs_resp.json()[0]['id']

        data = {
            "fieldId": fieldId
        }
        log.debug(f'Adding field "{fieldId}" to "{screenId}" issue screen in the tab {tabId} of project "{projectKey}" ...')

        resp = requests.post(
            f'{credentials.INSTANCE}/rest/api/3/screens/{screenId}/tabs/{tabId}/fields', 
            auth=(credentials.USER, credentials.TOKEN), 
            data=json.dumps(data), 
            headers={'Content-Type': 'application/json'}
        )
        resp.raise_for_status()
    
