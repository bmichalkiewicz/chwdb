import logging
import json
import requests
import os
import datetime
import azure.functions as func
from dateutil.relativedelta import relativedelta
from pprint import pprint
from pathlib import Path

def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    
    # Jira Variables
    headers = { "Content-Type" : "application/json" }
    JIRA_URL="https://test.atlassian.net/"
    path = Path(__file__).parent / "data/users.json"
    users_dict = {}
    users_list = []
    request_types = ['Test request type',
                      'test request type']
    # Slack Variables
    webhook_slack = ''
    data_slack = {'text': ""}

    # Validating and loading the request
    j = req.get_json()

    if not isinstance(j, (list, dict)):
        logging.info(j)
        return func.HttpResponse(j, status_code=501) 
   
    class User:
        requests = 0

        def __init__(self, token, email):
            self.token = token
            self.email = email
        
        @property
        def getemail(self):
            return self.email
        
        @property
        def gettoken(self):
            return self.token

        def transition_request(self, transition_number):
            new_transition = { 
            "transition": { 
                "id": transition_number
                } 
            }
            url = JIRA_URL +"/rest/api/2/issue/"+j["issue"]["key"]+"/transitions"
            requests.post(url, headers=headers, auth=(self.getemail, self.gettoken), data=json.dumps(new_transition))
        
    def assign_request(ClassUser):
        return ClassUser.transition_request(transition_number="51")

    def get_number_of_requests(user):
        url = JIRA_URL + "/rest/api/2/search?jql=project%20=Example%20AND%20status%20in%20(Closed,%20Resolved)%20AND%20resolved%20>%20startOfWeek()%20AND%20resolved%20<%20endOfWeek()%20AND%20assignee%20=%20currentUser()"
        issues = requests.get(url, headers=headers, auth=(user.getemail, user.gettoken)).json()
        number_of_requests = len(issues["issues"])
            
        return number_of_requests
    
    #Save and load dict with number of requests
    def save_data(data):
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
    
    def load_data():
        with open(path) as f:
            content = json.load(f)
        return content

    # Create new cache
    def update_data():
        one_hour_ago = datetime.datetime.now() - relativedelta(hours=1)
        data_time = datetime.datetime.fromtimestamp(os.path.getmtime(path))
        if data_time < one_hour_ago:
            pprint("Data is older than one hour ago, update data please...")
            return True
        else:
            return False
    
    def create_data(list_of_users):
        for user in list_of_users:
            json_user = {}
            json_user["login"] = user.getemail
            user.requests = get_number_of_requests(user)
            json_user["requests"] = user.requests
            users_list.append(json_user)
        save_data(users_list)
    
    def create_dict_with_users(users_list):
        for user in users_list:
            users_dict[user] = user.requests
        return users_dict
    
    #Slack Methods
    def slack_response(webhook, data):
        response = requests.post(webhook, data=json.dumps(data), headers=headers)
        if response.status_code != 200:
            raise ValueError('Request to slack returned an error %s, the response is \n%s' % (response.status_code, response.text))
        
    # Request Variables
    requesttype = j['issue']["fields"]["customfield_10030"]["requestType"]["name"]

    # Users
    Example_users = [User("TestAPI", "user@domain.com"), 
                    User("TestAPI", "user@domain.com"),
                    User("TestAPI", "user@domain.com"),
                    User("TestAPI", "user@domain.com")
    ]

    if path.is_file():
        if update_data():
            create_data(Example_users)
        else:
            file = load_data()
            for o in file:
                for u in Example_users:
                    if o["login"] == u.getemail:
                        u.requests = o["requests"]
    else:
        create_data(Example_users)

    users_dict = create_dict_with_users(Example_users)
    the_weakest_user = min(users_dict, key=users_dict.get)
    data_slack["text"] = ':loudspeaker: Request: <' + JIRA_URL + "browse/" + j["issue"]["key"] + "|" + j["issue"]["key"] + "> Assigned to " + the_weakest_user.getemail + " :shipit:"

    # Assigment mechanism

    pprint(j["issue"]["key"])
    
    try:
        if requesttype in request_types:
            assign_request(the_weakest_user)
            slack_response(webhook_slack, data_slack)
            return func.HttpResponse(j["issue"]["key"] + f": " + requesttype, status_code=200)
        else:
            return func.HttpResponse(f"Skip", status_code=400)          
    except TypeError:
        pprint("Not found service field")
        return func.HttpResponse(f"Skip", status_code=400)