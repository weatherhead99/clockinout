#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 24 23:45:51 2020

@author: danw
"""

import click
from clockinout_client.sync_client import ClockinoutSyncClient
from clockinout_protocols.clockinoutservice_pb2 import empty, UserInfo, OrgInfo
from clockinout_protocols.clockinout_queries_pb2 import UserQueryRequest, OrgQueryRequest
from tabulate import tabulate

@click.group()
@click.option("-c", "--connstr", type=str, default="localhost:50051")
@click.pass_context
def clockinoutsh(ctx, connstr):
    print("connecting to %s" % connstr)
    sclient = ClockinoutSyncClient(connstr)
    server_info = sclient.GetServerInfo(empty())
    print("connected to a server with version: %s" % server_info.version)
    ctx.obj = sclient

@clockinoutsh.command()
def version():
    pass

@clockinoutsh.command()
@click.option("-i", "--itemtp", type=click.Choice(["org","user"]), default="user")
@click.pass_context
def list_items(ctx, itemtp):
    sclient = ctx.parent.obj

    if itemtp == "user":
        user_list = sclient.QueryUsers(UserQueryRequest(user_filter=UserInfo()))
        tbl = {"name": [_.user.name for _ in user_list.results],
               "id" : [_.user.id for _ in user_list.results],
               "power_level" : [_.user.power_level for _ in user_list.results],
               "created" : [_.user.created.ToDatetime() for _ in user_list.results]}
        print(tabulate(tbl,headers="keys", tablefmt="fancy_grid"))
        return 
    else:
        org_list = sclient.QueryOrgs(OrgQueryRequest(org_filter=OrgInfo()))
        tbl = {"name" : [_.org.name for _ in org_list.results],
               "id" : [_.org.id for _ in org_list.results],
               "admin_user" : [_.org.admin_user.name for _ in org_list.results]}
        print(tabulate(tbl,headers="keys", tablefmt="fancy_grid"))


@clockinoutsh.command()
@click.option("-i", "--itemtp", type=click.Choice(["org","user"]), default="user")
@click.option("-q", "--query", prompt=True)
@click.pass_context
def inspect_item(ctx, itemtp, query):
    sclient = ctx.parent.obj
    
    print("querying for item of type %s" % itemtp)
    try:
        query = int(query)
        qfield = "id"
        print("querying by id...")
    except ValueError:
        qfield = "name"
        print("querying by name...")
    
    if itemtp == "user":
        ui = UserInfo()
        setattr(ui, qfield, query)
        req = UserQueryRequest(user_filter=ui, return_orgs=True, return_sessions=True,
                               return_tags=True)
        resp = sclient.QueryUsers(req)
        if len(resp.results) == 0:
            print("no matching items found")
        for u in resp.results:
            print(u.user)
        return

if __name__ == "__main__":
    clockinoutsh()