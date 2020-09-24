import requests
import json
import credentials

import logging
log = logging.getLogger(__name__)

XRAY_API = 'https://xray.cloud.xpand-it.com/api/v1'

class XrayAPI:
    def __init__(self):
        self.token = ''

    def authenticate(self):
        log.debug('Authenticating with Xray API...')

        json_data = json.dumps({"client_id": credentials.CLIENT_ID, "client_secret": credentials.CLIENT_SECRET})
        
        resp = requests.post(f'{XRAY_API}/authenticate', data=json_data, headers={'Content-Type':'application/json'})
        resp.raise_for_status()
        
        self.token = 'Bearer ' + resp.text.replace("\"","")

        # log.debug(f'Token: {self.token}')

    def createFolder(self, path, projectId = None, testPlanId = None):
        if (testPlanId == None):
            log.debug(f'Creating Folder "{path}" in project "{projectId}"...')

            json_data = f'mutation {{ createFolder( projectId: "{projectId}", path: "{path}") {{ warnings }} }}'
        else:
            log.debug(f'Creating Folder "{path}" in Test Plan "{testPlanId}"...')

            json_data = f'mutation {{ createFolder( testPlanId: "{testPlanId}", path: "{path}") {{ warnings }} }}'

        resp = requests.post(f'{XRAY_API}/graphql', json={ "query": json_data }, headers={'Content-Type':'application/json', 'Authorization': self.token})
        resp.raise_for_status()
    
        return resp.json()

    def addTestsToFolder(self, path, testIssueIds, projectId = None, testPlanId = None):
        testIssueIds_json = json.dumps(testIssueIds)

        if (testPlanId == None):
            log.debug(f'Adding tests to "{path}" in project "{projectId}"...')

            json_data = f'mutation {{ addTestsToFolder( projectId: "{projectId}", path: "{path}", testIssueIds: {testIssueIds_json}) {{ warnings }} }}'
        else:
            log.debug(f'Adding tests to "{path}" in Test Plan "{testPlanId}"...')

            json_data = f'mutation {{ addTestsToFolder( testPlanId: "{testPlanId}", path: "{path}", testIssueIds: {testIssueIds_json}) {{ warnings }} }}'

        resp = requests.post(f'{XRAY_API}/graphql', json={ "query": json_data }, headers={'Content-Type':'application/json', 'Authorization': self.token})
        resp.raise_for_status()
    
        return resp.json()


    def createTest(self, summary, description, projectId, testType, folder, gherkin, definition, steps):
        log.debug(f'Creating Test "{summary}"...')

        summary = summary.replace('"', '\\"')
        description = description.replace('"', '\\"')

        if (testType == 'Cucumber'):
            ctn = gherkin.replace('"', '\\"')
            content = f'gherkin: "{ctn}"'.replace('\n', '\\n')
        elif (testType == 'Manual'):
            content = 'steps: ' + json.dumps(steps).replace('"action"', 'action').replace('"data"', 'data').replace('"result"', 'result')
        else:
            ctn = definition.replace('"', '\\"')
            content = f'unstructured: "{ctn}"'

        json_data = f'''
            mutation {{
                createTest(
                    testType: {{ name: "{testType}" }},
                    {content},
                    folderPath: "{folder}"
                    jira: {{
                        fields: {{ summary: "{summary}", project: {{ id: "{projectId}" }} }}
                    }}
                ) {{
                    test {{
                        issueId
                        jira(fields: ["key"])
                    }}
                    warnings
                }}
            }}
        '''

        resp = requests.post(f'{XRAY_API}/graphql', json={ "query": json_data }, headers={'Content-Type':'application/json', 'Authorization': self.token})
        resp.raise_for_status()
    
        return resp.json()

    def createPrecondition(self, summary, description, projectId, preconditionType, steps, testIssueIds):
        log.debug(f'Creating Precondition "{summary}"...')

        summary = summary.replace('"', '\\"')
        description = description.replace('"', '\\"').replace('\n', '\\n')
        steps = steps.replace('"', '\\"').replace('\n', '\\n')

        testIssueIds_json = json.dumps(testIssueIds)

        json_data = f'''
            mutation {{
                createPrecondition(
                    preconditionType: {{ name: "{preconditionType}" }},
                    definition: "{steps}",
                    testIssueIds: {testIssueIds_json}
                    jira: {{
                        fields: {{ summary: "{summary}", description: "{description}", project: {{ id: "{projectId}" }} }}
                    }}
                ) {{
                    precondition {{
                        issueId
                        jira(fields: ["key"])
                    }}
                    warnings
                }}
            }}
        '''

        resp = requests.post(f'{XRAY_API}/graphql', json={ "query": json_data }, headers={'Content-Type':'application/json', 'Authorization': self.token})
        resp.raise_for_status()
    
        return resp.json()

    def createTestSet(self, summary, description, projectId, testIssueIds):
        log.debug(f'Creating Test Set "{summary}"...')

        summary = summary.replace('"', '\\"')
        description = description.replace('"', '\\"').replace('\n', '\\n')

        testIssueIds_json = json.dumps(testIssueIds)

        json_data = f'''
            mutation {{
                createTestSet(
                    testIssueIds: {testIssueIds_json}
                    jira: {{
                        fields: {{ summary: "{summary}", description: "{description}", project: {{ id: "{projectId}" }} }}
                    }}
                ) {{
                    testSet {{
                        issueId
                        jira(fields: ["key"])
                    }}
                    warnings
                }}
            }}
        '''

        resp = requests.post(f'{XRAY_API}/graphql', json={ "query": json_data }, headers={'Content-Type':'application/json', 'Authorization': self.token})
        resp.raise_for_status()
    
        return resp.json()

    def createTestPlan(self, summary, description, projectId, fixVersions, testIssueIds):
        log.debug(f'Creating Test Plan "{summary}"...')

        summary = summary.replace('"', '\\"')
        description = description.replace('"', '\\"').replace('\n', '\\n')

        testIssueIds_json = json.dumps(testIssueIds)

        fixVersionObjs = list(map(lambda v: { "name": v }, fixVersions))
        fixVersions_json = json.dumps(fixVersionObjs).replace('"name"', 'name')

        json_data = f'''
            mutation {{
                createTestPlan(
                    testIssueIds: {testIssueIds_json}
                    jira: {{
                        fields: {{ summary: "{summary}", description: "{description}", project: {{ id: "{projectId}" }}, fixVersions: {fixVersions_json} }}
                    }}
                ) {{
                    testPlan {{
                        issueId
                        jira(fields: ["key"])
                    }}
                    warnings
                }}
            }}
        '''

        resp = requests.post(f'{XRAY_API}/graphql', json={ "query": json_data }, headers={'Content-Type':'application/json', 'Authorization': self.token})
        resp.raise_for_status()
    
        return resp.json()

    def importXrayJsonResults(self, results):
        json_data = json.dumps(results)
        
        resp = requests.post(f'{XRAY_API}/import/execution', data=json_data, headers={'Content-Type':'application/json', 'Authorization': self.token})
        resp.raise_for_status()
        
        return resp.json()

    def importCucumberResults(self, results, info):
        resp = requests.post(f'{XRAY_API}/import/execution/cucumber/multipart', files={'results': results, 'info': info}, headers={'Authorization': self.token})
        resp.raise_for_status()
        
        return resp.json()

    def importRobotResults(self, results, info):
        resp = requests.post(f'{XRAY_API}/import/execution/robot/multipart', files={'results': results, 'info': info}, headers={'Authorization': self.token})
        resp.raise_for_status()
        
        return resp.json()

    def importNUnitResults(self, results, info):
        resp = requests.post(f'{XRAY_API}/import/execution/nunit/multipart', files={'results': results, 'info': info}, headers={'Authorization': self.token})
        resp.raise_for_status()
        
        return resp.json()

    def importTestNGResults(self, results, info):
        resp = requests.post(f'{XRAY_API}/import/execution/testng/multipart', files={'results': results, 'info': info}, headers={'Authorization': self.token})
        resp.raise_for_status()
        
        return resp.json()

    def importJUnitResults(self, results, info):
        resp = requests.post(f'{XRAY_API}/import/execution/junit/multipart', files={'results': results, 'info': info}, headers={'Authorization': self.token})
        resp.raise_for_status()
        
        return resp.json()


