# Author:Jesi
# Time : 2018/9/17 13:44
from django import template
register=template.Library()

@register.inclusion_tag("rbac/menu.html")
def get_menu(request,):
    menu_permission_list=request.session["menu_permission_list"]
    return {"menu_permission_list":menu_permission_list}