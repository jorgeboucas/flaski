import io
import os
import json
import base64
import tempfile
import pandas as pd
import dash_bootstrap_components as dbc
from dash import dcc, html
import traceback
from myapp.email import send_email
from myapp import app
from datetime import datetime
from flask import render_template

def parse_table(contents,filename,last_modified,session_id,cache):
    # @cache.memoize(timeout=3600)
    def _parse_table(contents,filename,last_modified,session_id,cache):
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        extension=filename.split(".")[-1]
        if extension == 'csv':
            # Assume that the user uploaded a CSV file
            df = pd.read_csv(
                io.StringIO(decoded.decode('utf-8')))
        elif extension == 'tsv':
            df = pd.read_csv(
                io.StringIO(decoded.decode('utf-8')), sep="\t")
        elif extension in ['xls', "xlsx"] :
            # Assume that the user uploaded an excel file
            df = pd.read_excel(io.BytesIO(decoded))
        return df.to_json()
    return pd.read_json(_parse_table(contents,filename,last_modified,session_id,cache))

def make_options(valuesin):
    opts=[]
    for c in valuesin:
        opts.append( {"label":c, "value":c} )
    return opts

def make_except_toast(text=None,id=None,e=None,user=None, eapp=None):
    if e:
        tb_str = ''.join(traceback.format_exception(None, e, e.__traceback__))

        emsg_html=tb_str.split("\n")
        send_email(
            '[Flaski] exception: %s ' %eapp,
            sender=app.config['MAIL_USERNAME'],
            recipients=app.config['ADMINS'],
            text_body=render_template(
                'email/app_exception.txt',
                user=user, 
                eapp=eapp, 
                emsg=tb_str, 
                etime=str(datetime.now())
            ),
            html_body=render_template(
                'email/app_exception.html',
                user=user, 
                eapp=eapp, 
                emsg=emsg_html, 
                etime=str(datetime.now())
            ),
            reply_to=user.email 
        )

        text=[ text,
            dcc.Markdown(f'```{e}```'),
            "Something went wrong, we have been notified. If you would like to share your session with us and get help on this issue please press 'Ice Cream'.",
            dbc.Collapse(
                dbc.Card(
                    dbc.CardBody(
                        dcc.Markdown(f'```{tb_str}```'),
                    ),
                    color="light",
                ),
                id={'type':'collapse-toast-traceback','index':id},
                is_open=False,
                style={"margin-top":"10px","margin-bottom":"10px"}
            )
        ]
        is_open=True
    else:
        text=[]
        is_open=False


    toast=dbc.Toast( text+
        [
            html.Div(
                [
                    dbc.Button("expand", outline=True, color="dark",id={'type':'toggler-toast-traceback','index':id},size="sm", style={"margin-right":"2px"} ),
                    dbc.Button("Ice Cream", outline=True, color="dark",id={'type':'help-toast-traceback','index':id},size="sm", style={"margin-left":"2px"} )
                ],
                className="d-grid gap-2 d-md-flex justify-content-md-end",
                style={"margin-top":"10px"} 
            ),
        ],
        id={'type':'toast-error','index':id},
        header="Exception",
        is_open=is_open,
        dismissable=True,
        icon="danger",
        # top: 66 positions the toast below the navbar
        # style={"position": "fixed", "z-index": 0, "top": 66, "right": 10, "width": 350,},
    )
    return toast

def ask_for_help(tb_str, user, current_app, session_data=None ):
    
    if session_data:
        session_data=session_data["session_data"]
        share_folder=os.path.join(app.config["USERS_DATA"], 'shared_sessions')
        if not os.path.isdir(share_folder):
            os.makedirs(share_folder)
        session_file=tempfile.NamedTemporaryFile(dir=share_folder, suffix=".ses")
        with open(session_file,"w") as fout:
            json.dump(session_data, fout)
    else:
        session_file="no session file for this Exception"

    send_email('[Flaski] help needed: %s ' %current_app,
        sender=app.config['MAIL_USERNAME'],
        recipients=app.config['ADMINS'],
        text_body=render_template('email/app_help.txt',
                                    user=user, eapp=current_app, emsg=tb_str, etime=str(datetime.now()), session_file=session_file),
        html_body=render_template('email/app_help.html',
                                    user=user, eapp=current_app, emsg=tb_str.split("\n"), etime=str(datetime.now()), session_file=session_file),\
        reply_to=user.email )      