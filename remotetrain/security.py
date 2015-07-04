USERS = {'editor':'8d!t@r',
          'viewer':'v!8w8r'}
GROUPS = {'viewer':['group:viewers'],
          'editor':['group:viewers', 'group:editors']}

def groupfinder(userid, request):
    if userid in USERS:
        return GROUPS.get(userid, [])

