# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.4.2
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Example of token operations
#
# Use device-flow or similar to obtain token

# %%
import requests
import json
from pathlib import Path
import time
import subprocess
import re
from datetime import datetime
import types

# %%
base_path = Path('.')

# %%
token_family = 'todocli-config'

# %% [markdown]
# ## Load token and check against MS Graph

# %%
org_token_path = sorted(base_path.glob(f'{token_family}-token-*.json'))[-1]
print(f'Reading access token from {org_token_path}')
result = json.load(org_token_path.open())
token, config = (types.SimpleNamespace(**result[k]) for k in ['response', 'config'])


# %%
# You can find more Microsoft Graph API endpoints from Graph Explorer
# https://developer.microsoft.com/en-us/graph/graph-explorer
ENDPOINT = 'https://graph.microsoft.com/v1.0/me'  # This resource requires no admin consent
graph_response = requests.get(
    ENDPOINT, 
    headers={
        'Authorization': "Bearer "+token.access_token
    })
graph_response if not graph_response.ok else graph_response.json()

# %% [markdown]
# ## Try creating a task
#
# Cannot mix scopes: https://stackoverflow.com/questions/39492243/office-api-v2-authentication-multiple-resources-in-scopes
# Required scope: `https://outlook.office.com/tasks.readwrite`
#
# > Tasks are organized in task folders which are in turn organized in task groups. Each mailbox has a default task folder (with the Name property Tasks) and a default task group (Name property is My Tasks).
#
#
# https://docs.microsoft.com/en-us/previous-versions/office/office-365-api/api/version-2.0/task-rest-operations
# not graph planner api 
# https://docs.microsoft.com/en-us/graph/api/resources/plannertask?view=graph-rest-1.0
#
#
# https://docs.microsoft.com/en-us/previous-versions/office/office-365-api/api/version-2.0/complex-types-for-mail-contacts-calendar#TaskResource
#

# %%
ENDPOINT = 'https://outlook.office.com/api/v2.0/me/tasks'
task = {
    'Subject': 'Test task from todocli',
    'Body': {'ContentType': '1', 'Content': 'This is the <b>body</b> of the task'}
}

response = requests.post(
    ENDPOINT, 
    headers={
        'Authorization': "Bearer "+token.access_token
    }, json = task)

response.text

# %%
