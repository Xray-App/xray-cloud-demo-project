import jira
import xray
import credentials
import json
import random
import string
import re
import sys
import logging
from collections import defaultdict
from requests.exceptions import HTTPError
import argparse

log = logging.getLogger('demo')
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

class Scope:
    def __init__(self):
        self.accountId = ''
        self.projectKey = ''
        self.projectId = ''
        self.issues = {}
        self.issueTypes = {}
        self.fields = {}
        self.tests = {}
        self.preConditions = {}
        self.testSets = {}
        self.testPlans = {}

    def withProject(self, project):
        self.projectKey = project.key
        self.projectId = project.id
        return self

    def withIssueTypes(self, issueTypesList):
        for it in issueTypesList:
            self.issueTypes[it['name']] = it
        return self

    def withFields(self, fields):
        for field in fields:
            name = field.get('untranslatedName', field.get('name', ''))
            self.fields[name] = field
        return self

    def withIssue(self, externalKey, issue):
        if (externalKey):
            self.issues[externalKey] = issue
        return self

    def withTest(self, externalKey, test):
        if (externalKey):
            self.tests[externalKey] = test
        return self

    def withPrecondition(self, externalKey, precond):
        if (externalKey):
            self.preConditions[externalKey] = precond
        return self

    def withTestSet(self, externalKey, testSet):
        if (externalKey):
            self.testSets[externalKey] = testSet
        return self

    def withTestPlan(self, externalKey, testPlan):
        if (externalKey):
            self.testPlans[externalKey] = testPlan
        return self

def setup(scope):
    log.info('[Setup]')

    users = jira.searchUser(credentials.USER)
    user = next(filter(lambda u: u['emailAddress'] == credentials.USER, users), None)
    if (user):
        accountId = user['accountId']
        scope.accountId = accountId
    else:
        raise Exception('Couldn\'t find default user!')

    xrayApi = xray.XrayAPI()
    xrayApi.authenticate()

    return xrayApi

def getRandomProjectName():
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(3))

def createProject(data, scope, withSalt):
    log.info('[Step 1] - Creating Project ...')
    
    if (withSalt == True): 
        salt = getRandomProjectName()
    else:
        salt = ''
    
    projectKey = data['project']['key'] + salt
    projectName = data['project']['name'] + salt
    project = jira.createProject(
        key = projectKey, 
        name = projectName, 
        description = data['project'].get('description', ''), 
        url = data['project'].get('url', ''), 
        accountId = scope.accountId)

    log.debug(f'Project: {projectKey} - {projectName}')
    
    issueTypeScheme = jira.getIssueTypeSchemeForProject(project.id)
    issueTypeSchemeItems = jira.getIssueTypeSchemeItems(issueTypeScheme.id)
    issueTypes = jira.getIssueTypes()

    scope.withIssueTypes(issueTypes)

    xrayIssueTypeIds = list(map(lambda it: it['id'], filter(lambda it: isXrayIssueType(it), issueTypes)))
    
    if (len(xrayIssueTypeIds) < 6):
        raise Exception('Xray Issue Types missing!')

    jira.addIssueTypeSchemeItems(issueTypeScheme.id, xrayIssueTypeIds)

    # Create components
    for c in data['project']['components']:
        jira.createComponent(c.get('name', ''), c.get('description', ''), project.key, scope.accountId)

    # Create versions
    for v in data['project'].get('versions', []):
        jira.createVersion(v.get('name', ''), v.get('description', ''), project.id)

    fields = jira.getIssueFields()
    scope.withFields(fields)

    # Add Epic name field to screen
    epicNameCFId = scope.fields['Epic Name']['id']
    epicLinkCFId = scope.fields['Epic Link']['id']
    
    jira.AddFieldToDefaultProjectScreen(epicNameCFId, project.key)
    jira.AddFieldToDefaultProjectScreen(epicLinkCFId, project.key)
    
    scope.withProject(project)

    return scope


def isXrayIssueType(issueType):
    if (issueType.get('scope')): # skip next get issue types
        return False
    props = jira.getIssueTypeProperties(issueType['id'])
    for p in props:
        if p.key.startswith('com.xpandit.xray'):
            issueType['xrayProp'] = p.key # adding Xray entity property to object
            return True
    return False

def createEpicsAndStories(data, scope):
    log.info('[Step 2] - Creating Epics and Stories...')

    epicNameCFId = scope.fields['Epic Name']['id']
    epicLinkCFId = scope.fields['Epic Link']['id']

    for issue in data.get('issues', []):
        summary = issue.get('summary', '')
        description = issue.get('description', '')
        projectId = scope.projectId
        issueTypeName = issue.get('issueType', '')
        components = issue.get('components', [])
        fixVersions = issue.get('fixVersions', [])
        epicName = issue.get('epicName', None)
        epicLink = issue.get('epicLink', None)
        epicLinkId = scope.issues[epicLink]['key'] if epicLink != None else None
        
        createdIssue = jira.createIssue(summary, description, projectId, issueTypeName, components, fixVersions, epicName, epicLinkId, epicNameCFId, epicLinkCFId)
        
        scope.withIssue(issue['extKey'], createdIssue)
        if (issue['issueType'] == 'Epic'):
            scope.withIssue(issue['epicName'], createdIssue)

    return scope


def createTests(data, scope, xray):
    log.info('[Step 3] - Creating Tests ...')

    folders = set()

    for test in data.get('tests', []):
        summary = test.get('summary', '')
        description = test.get('description', '')
        projectId = scope.projectId
        testType = test.get('testType', 'Manual')
        folder = test.get('folder', '/')
        gherkin = test.get('gherkin', '')
        definition = test.get('definition', '')
        steps = test.get('steps', [])

        # ensure folder is created
        if (folder != '/' and folder not in folders):
            xray.createFolder(folder, projectId)
            folders.add(folder)

        createdTest = xray.createTest(summary, description, projectId, testType, folder, gherkin, definition, steps)

        issueKey = createdTest.get('data', {}).get('createTest', {}).get('test', {}).get('jira', {}).get('key', None)

        req = test.get('tests', None)
        if (req and issueKey):
            targetIssue = scope.issues.get(req, None)
            if (targetIssue):
                jira.createIssueLink(issueKey, targetIssue['key'], "Test")
        
        scope.withTest(test['extKey'], createdTest)

def createPreconditions(data, scope, xray):
    log.info('[Step 4] - Creating Preconditions ...')

    for precond in data.get('preConditions', []):
        summary = precond.get('summary', '')
        description = precond.get('description', '')
        projectId = scope.projectId
        preconditionType = precond.get('preconditionType', 'Manual')
        steps = precond.get('steps', '')
        tests = precond.get('tests', [])

        testIssueIds = list(
            filter(
                None, 
                map(
                    lambda test: scope.tests.get(test, {}).get('data', {}).get('createTest', {}).get('test', {}).get('issueId', None),
                    tests
                )
            )
        )

        createdPrecond = xray.createPrecondition(summary, description, projectId, preconditionType, steps, testIssueIds)

        scope.withPrecondition(precond['extKey'], createdPrecond)

def createTestSets(data, scope, xray):
    log.info('[Step 5] - Creating Test Sets ...')

    for testSet in data.get('testSets', []):
        summary = testSet.get('summary', '')
        description = testSet.get('description', '')
        projectId = scope.projectId
        tests = testSet.get('tests', [])

        testIssueIds = list(
            filter(
                None, 
                map(
                    lambda test: scope.tests.get(test, {}).get('data', {}).get('createTest', {}).get('test', {}).get('issueId', None),
                    tests
                )
            )
        )

        createdTestSet = xray.createTestSet(summary, description, projectId, testIssueIds)

        scope.withTestSet(testSet['extKey'], createdTestSet)


def createTestPlans(data, scope, xray):
    log.info('[Step 6] - Creating Test Plan ...')

    for testPlan in data.get('testPlans', []):
        summary = testPlan.get('summary', '')
        description = testPlan.get('description', '')
        projectId = scope.projectId
        fixVersions = testPlan.get('fixVersions', [])
        tests = testPlan.get('tests', [])

        testIssueIds = list(
            filter(
                None, 
                map(
                    lambda test: scope.tests.get(test['extKey'], {}).get('data', {}).get('createTest', {}).get('test', {}).get('issueId', None),
                    tests
                )
            )
        )

        createdTestPlan = xray.createTestPlan(summary, description, projectId, fixVersions, testIssueIds)
        testPlanId = createdTestPlan.get('data', {}).get('createTestPlan', {}).get('testPlan', {}).get('issueId', None)

        # Add Tests to Test Plan folders
        folders = defaultdict(list)
        for test in tests:
            folder = test.get('folder', None)
            if folder != None and folder != '/':
                if folder not in folders:
                    xray.createFolder(folder, None, testPlanId)
                testIssueId = scope.tests.get(test['extKey'], {}).get('data', {}).get('createTest', {}).get('test', {}).get('issueId', None)
                if testIssueId != None:
                    folders[folder].append(testIssueId)
                
        for f in folders:
            xray.addTestsToFolder(f, folders[f], testPlanId=testPlanId)

        scope.withTestPlan(testPlan['extKey'], createdTestPlan)

def importManualResults(data, scope, xray):
    log.info('[Step 7] - Importing Manual Execution Results ...')

    # replace external key references
    data.get('info', {})['project'] = scope.projectKey

    extTestPlanKey = data.get('info', {}).get('testPlanKey', None)
    if (extTestPlanKey != None):
        testPlanKey = scope.testPlans.get(extTestPlanKey, {}).get('data', {}).get('createTestPlan', {}).get('testPlan', {}).get('jira', {}).get('key', None)
        if (testPlanKey != None):
            data['info']['testPlanKey'] = testPlanKey

    tests = data.get('tests', [])
    for test in tests:
        # replace external test key
        extTestKey = test.get('testKey', None)
        if (extTestKey != None):
            testKey = scope.tests.get(extTestKey, {}).get('data', {}).get('createTest', {}).get('test', {}).get('jira', {}).get('key', None)
            if (testKey != None):
                test['testKey'] = testKey
        # replace external defect keys
        steps = test.get('steps', [])
        for step in steps:
            defectKeys = []
            defects = step.get('defects', [])
            if len(defects) > 0:
                for defect in defects:
                    defectKey = scope.issues.get(defect, {}).get('key', None)
                    if (defectKey != None):
                        defectKeys.append(defectKey)
                step['defects'] = defectKeys

    xray.importXrayJsonResults(data)


def importCucumberResults(data, info, scope, xray):
    log.info('[Step 8] - Importing Cucumber Execution Results ...')

    # replace external key references
    data = replaceTestExternalKeys(data, scope, '@TEST_')
    json_info = replaceInfoExternalKeys(info, scope)

    xray.importCucumberResults(data, json_info)

def replaceTestExternalKeys(data, scope, prefix = ''):
    pattern = re.compile(prefix + 'EXT-KEY-\\d+')

    testKeys = []
    matches = pattern.finditer(data)
    for match in matches:
        extTestKey = match.group().replace(prefix, '') if prefix else match.group()
        testKey = scope.tests.get(extTestKey, {}).get('data', {}).get('createTest', {}).get('test', {}).get('jira', {}).get('key', None)
        if (testKey != None):
            testKeys.append((match.group(), testKey))

    for testKeyTuple in testKeys:
        data = data.replace(testKeyTuple[0], prefix + testKeyTuple[1])

    return data

def replaceInfoExternalKeys(info, scope):
    json_info = json.loads(info)
    json_info.get('fields', {}).get('project', {})['id'] = scope.projectId

    xrayFields = json_info.get('xrayFields', {})
    extTestPlanKey = xrayFields.get('testPlanKey', None)
    if (extTestPlanKey):
        testPlanKey = scope.testPlans.get(extTestPlanKey, {}).get('data', {}).get('createTestPlan', {}).get('testPlan', {}).get('jira', {}).get('key', None)
        xrayFields['testPlanKey'] = testPlanKey

    return json.dumps(json_info)

def importRobotResults(data, info, scope, xray):
    log.info('[Step 9] - Importing Robot Execution Results ...')

    # replace external key references
    json_info = replaceInfoExternalKeys(info, scope)

    xray.importRobotResults(data, json_info)


def importNUnitResults(data, info, scope, xray):
    log.info('[Step 10] - Importing NUnit Execution Results ...')

    # replace external key references
    json_info = replaceInfoExternalKeys(info, scope)

    xray.importNUnitResults(data, json_info)

def importTestNGResults(data, info, scope, xray):
    log.info('[Step 11] - Importing TestNG Execution Results ...')

    # replace external key references
    json_info = replaceInfoExternalKeys(info, scope)

    xray.importTestNGResults(data, json_info)

def importJUnitResults(data, info, scope, xray):
    log.info('[Step 12] - Importing JUnit Execution Results ...')

    # replace external key references
    json_info = replaceInfoExternalKeys(info, scope)

    xray.importJUnitResults(data, json_info)

def main(argv):
    verbose = False
    salt = False

    parser = argparse.ArgumentParser(description='Creates a demo Xray project in a Jira Software cloud instance.')
    parser.add_argument('-s', '--salt', action='store_true', help='appends 3 random chars to the project name (useful if you already have a project with the same name or key)')
    parser.add_argument('-v', '--verbose', action='store_true', help='enables verbose logging')

    args = parser.parse_args()
    
    logging.basicConfig(stream=sys.stdout, level=(logging.INFO if args.verbose == False else logging.DEBUG))

    scope = Scope()

    try:
        xrayApi = setup(scope)

        with open('resources/data.json') as json_file:
            data = json.load(json_file)

            createProject(data, scope, args.salt)
            createEpicsAndStories(data, scope)
            createTests(data, scope, xrayApi)
            createPreconditions(data, scope, xrayApi)
            createTestSets(data, scope, xrayApi)
            createTestPlans(data, scope, xrayApi)
        
        with open('resources/manual-test-results.json') as data_file:
            data = json.load(data_file)
            importManualResults(data, scope, xrayApi)

        with open('resources/cucumber-results.json') as data_file:
            with open('resources/cucumber-info.json') as info_file:
                data = data_file.read()
                info = info_file.read()
                importCucumberResults(data, info, scope, xrayApi)

        with open('resources/robot-results.xml') as data_file:
            with open('resources/robot-info.json') as info_file:
                data = data_file.read()
                info = info_file.read()
                importRobotResults(data, info, scope, xrayApi)

        with open('resources/nunit-results.xml') as data_file:
            with open('resources/nunit-info.json') as info_file:
                data = data_file.read()
                info = info_file.read()
                importNUnitResults(data, info, scope, xrayApi)

        with open('resources/testng-results.xml') as data_file:
            with open('resources/testng-info.json') as info_file:
                data = data_file.read()
                info = info_file.read()
                importTestNGResults(data, info, scope, xrayApi)

        with open('resources/junit-results.xml') as data_file:
            with open('resources/junit-info.json') as info_file:
                data = data_file.read()
                info = info_file.read()
                importJUnitResults(data, info, scope, xrayApi)

        log.info(f'All Done. Please check project with key {scope.projectKey}.')
        log.info('Enjoy. Bye!')
    except HTTPError as e:
        log.error(f'HTTP Error {e.response.status_code}: {e.response.text}')
        exit(2)

if __name__ == '__main__':
    main(sys.argv[1:])
