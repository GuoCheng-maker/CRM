from django.test import TestCase

# Create your tests here.
l=['/users/', '/users/add', '/users/delete/(\d+)', 'users/edit/(\d+)']


c_path="roles/"

import re

flag=False

for permission in l:

    permission="^%s$"%permission
    ret=re.match(permission,c_path)
    if ret:
        flag=True
        break

if flag:
    print("success")








#
#
# import re
# ret=re.match('^/users/$',"/users/delete/9")
# print(ret)