from flask import render_template, Flask, Response, request, url_for, redirect, session, send_file, flash, jsonify
from flaski import app
from werkzeug.utils import secure_filename
from flask_session import Session
from flaski.forms import LoginForm
from flask_login import current_user, login_user, logout_user, login_required
from datetime import datetime
from flaski import db
from werkzeug.urls import url_parse
from flaski.apps.main.iscatterplot import make_figure, figure_defaults
from flaski.models import User, UserLogging
from flaski.routines import session_to_file
from flaski.routes import FREEAPPS
from flaski.email import send_exception_email
import plotly
import plotly.io as pio


import os
import io
import sys
import random
import json

import pandas as pd

import base64

ALLOWED_EXTENSIONS=["xlsx","tsv","csv"]
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/iscatterplot/<download>', methods=['GET', 'POST'])
@app.route('/iscatterplot', methods=['GET', 'POST'])
@login_required
def iscatterplot(download=None):
    """ 
    renders the plot on the fly.
    https://gist.github.com/illume/1f19a2cf9f26425b1761b63d9506331f
    """       

    apps=FREEAPPS+session["PRIVATE_APPS"]

    if request.method == 'POST':

        # READ SESSION FILE IF AVAILABLE 
        # AND OVERWRITE VARIABLES
        inputsessionfile = request.files["inputsessionfile"]
        if inputsessionfile:
            if inputsessionfile.filename.rsplit('.', 1)[1].lower() != "ses"  :
                plot_arguments=session["plot_arguments"]
                error_msg="The file you have uploaded is not a session file. Please make sure you upload a session file with the correct `ses` extension."
                flash(error_msg,'error')
                return render_template('/apps/iscatterplot.html' , filename=session["filename"], apps=apps, **plot_arguments)

            session_=json.load(inputsessionfile)
            if session_["ftype"]!="session":
                plot_arguments=session["plot_arguments"]
                error_msg="The file you have uploaded is not a session file. Please make sure you upload a session file."
                flash(error_msg,'error')
                return render_template('/apps/iscatterplot.html' , filename=session["filename"], apps=apps, **plot_arguments)

            if session_["app"]!="iscatterplot":
                plot_arguments=session["plot_arguments"]
                error_msg="The file was not load as it is associated with the '%s' and not with this app." %session_["app"]
                flash(error_msg,'error')
                return render_template('/apps/iscatterplot.html' , filename=session["filename"], apps=apps, **plot_arguments)
    
            del(session_["ftype"])
            del(session_["COMMIT"])
            for k in list(session_.keys()):
                session[k]=session_[k]
            plot_arguments=session["plot_arguments"]
            flash('Session file sucessufuly read.')


        # READ ARGUMENTS FILE IF AVAILABLE 
        # AND OVERWRITE VARIABLES
        inputargumentsfile = request.files["inputargumentsfile"]
        if inputargumentsfile :
            if inputargumentsfile.filename.rsplit('.', 1)[1].lower() != "arg"  :
                plot_arguments=session["plot_arguments"]
                error_msg="The file you have uploaded is not a arguments file. Please make sure you upload a session file with the correct `arg` extension."
                flash(error_msg,'error')
                return render_template('/apps/iscatterplot.html' , filename=session["filename"], apps=apps, **plot_arguments)

            session_=json.load(inputargumentsfile)
            if session_["ftype"]!="arguments":
                plot_arguments=session["plot_arguments"]
                error_msg="The file you have uploaded is not an arguments file. Please make sure you upload an arguments file."
                flash(error_msg,'error')
                return render_template('/apps/iscatterplot.html' , filename=session["filename"], apps=apps, **plot_arguments)

            if session_["app"]!="iscatterplot":
                plot_arguments=session["plot_arguments"]
                error_msg="The file was not loaded as it is associated with the '%s' and not with this app." %session_["app"]
                flash(error_msg,'error')
                return render_template('/apps/iscatterplot.html' , filename=session["filename"], apps=apps, **plot_arguments)

            del(session_["ftype"])
            del(session_["COMMIT"])
            for k in list(session_.keys()):
                session[k]=session_[k]
            plot_arguments=session["plot_arguments"]
            flash('Arguments file sucessufuly read.',"info")
        
        # IF THE UPLOADS A NEW FILE 
        # THAN UPDATE THE SESSION FILE
        # READ INPUT FILE
        inputfile = request.files["inputfile"]
        if inputfile:
            filename = secure_filename(inputfile.filename)
            if allowed_file(inputfile.filename):
                session["filename"]=filename
                fileread = inputfile.read()
                filestream=io.BytesIO(fileread)
                extension=filename.rsplit('.', 1)[1].lower()
                if extension == "xlsx":
                    df=pd.read_excel(filestream)
                elif extension == "csv":
                    df=pd.read_csv(filestream)
                elif extension == "tsv":
                    df=pd.read_csv(filestream,sep="\t")
                
                df=df.astype(str)
                session["df"]=df.to_json()
                
                cols=df.columns.tolist()

                if session["plot_arguments"]["groups"] not in cols:
                    session["plot_arguments"]["groups"]=["None"]+cols

                if session["plot_arguments"]["markerstyles_cols"] not in cols:
                    session["plot_arguments"]["markerstyles_cols"]=["select a column.."]+cols
                
                if session["plot_arguments"]["markerc_cols"] not in cols:
                    session["plot_arguments"]["markerc_cols"]=["select a column.."]+cols

                if session["plot_arguments"]["markersizes_cols"] not in cols:
                    session["plot_arguments"]["markersizes_cols"]=["select a column.."]+cols

                if session["plot_arguments"]["markeralpha_col"] not in cols:
                    session["plot_arguments"]["markeralpha_col"]=["select a column.."]+cols

                if session["plot_arguments"]["labels_col"] not in cols:
                    session["plot_arguments"]["labels_col"]=["select a column.."]+cols

                if session["plot_arguments"]["edgecolor_cols"] not in cols:
                    session["plot_arguments"]["edgecolor_cols"]=["select a column.."]+cols
        
                if session["plot_arguments"]["edge_linewidth_cols"] not in cols:
                    session["plot_arguments"]["edge_linewidth_cols"]=["select a column.."]+cols

                # IF THE USER HAS NOT YET CHOOSEN X AND Y VALUES THAN PLEASE SELECT
                if (session["plot_arguments"]["xvals"] not in cols) & (session["plot_arguments"]["yvals"] not in cols):

                    session["plot_arguments"]["xcols"]=cols
                    session["plot_arguments"]["xvals"]=cols[0]

                    session["plot_arguments"]["ycols"]=cols
                    session["plot_arguments"]["yvals"]=cols[1]
                                  
                    sometext="Please select which values should map to the x and y axes."
                    plot_arguments=session["plot_arguments"]
                    flash(sometext,'info')
                    return render_template('/apps/iscatterplot.html' , filename=filename, apps=apps,**plot_arguments)
                
            else:
                # IF UPLOADED FILE DOES NOT CONTAIN A VALID EXTENSION PLEASE UPDATE
                error_msg="You can can only upload files with the following extensions: 'xlsx', 'tsv', 'csv'. Please make sure the file '%s' \
                has the correct format and respective extension and try uploadling it again." %filename
                flash(error_msg,'error')
                return render_template('/apps/iscatterplot.html' , filename="Select file..", apps=apps, **plot_arguments)
        
        if not inputsessionfile and not inputargumentsfile:
            # SELECTION LISTS DO NOT GET UPDATED 
            lists=session["lists"]

            # USER INPUT/PLOT_ARGUMENTS GETS UPDATED TO THE LATEST INPUT
            # WITH THE EXCEPTION OF SELECTION LISTS
            plot_arguments = session["plot_arguments"]

            if plot_arguments["groups_value"]!=request.form["groups_value"]:
                if request.form["groups_value"]  != "None":
                    df=pd.read_json(session["df"])
                    df[request.form["groups_value"]]=df[request.form["groups_value"]].apply(lambda x: secure_filename(str(x) ) )
                    df=df.astype(str)
                    session["df"]=df.to_json()
                    groups=df[request.form["groups_value"]]
                    groups=list(set(groups))
                    groups.sort()
                    plot_arguments["list_of_groups"]=groups
                    groups_settings=[]
                    group_dic={}
                    for group in groups:
                        group_dic={"name":group,\
                            "markers":plot_arguments["markers"],\
                            "markersizes_col":"select a column..",\
                            "markerc":random.choice([ cc for cc in plot_arguments["marker_color"] if cc != "white"]),\
                            "markerc_col":"select a column..",\
                            "markerc_write":plot_arguments["markerc_write"],\
                            "edge_linewidth":plot_arguments["edge_linewidth"],\
                            "edge_linewidth_col":"select a column..",\
                            "edgecolor":plot_arguments["edgecolor"],\
                            "edgecolor_col":"select a column..",\
                            "edgecolor_write":"",\
                            "marker":random.choice(plot_arguments["markerstyles"]),\
                            "markerstyles_col":"select a column..",\
                            "marker_alpha":plot_arguments["marker_alpha"],\
                            "markeralpha_col_value":"select a column.."}
                        groups_settings.append(group_dic)
                        # for k in list( group_dic[group].keys() ):
                        #     plot_arguments[k+"_"+group]=group_dic[group][k]
                    plot_arguments["groups_settings"]=groups_settings
                elif request.form["groups_value"] == "None" :
                    plot_arguments["groups_settings"]=[]
                    plot_arguments["list_of_groups"]=[]

            elif plot_arguments["groups_value"] != "None":
                # print(list(request.form.keys()) )
                # import sys
                # sys.stdout.flush()
                groups_settings=[]
                group_dic={}
                for group in plot_arguments["list_of_groups"]:
                    group_dic={"name":group,\
                        "markers":request.form["%s.markers" %group],\
                        "markersizes_col":request.form["%s.markersizes_col" %group],\
                        "markerc":request.form["%s.markerc" %group],\
                        "markerc_col":request.form["%s.markerc_col" %group],\
                        "markerc_write":request.form["%s.markerc_write" %group],\
                        "edge_linewidth":request.form["%s.edge_linewidth" %group],\
                        "edge_linewidth_col":request.form["%s.edge_linewidth_col" %group],\
                        "edgecolor":request.form["%s.edgecolor" %group],\
                        "edgecolor_col":request.form["%s.edgecolor_col" %group],\
                        "edgecolor_write":request.form["%s.edgecolor_write" %group],\
                        "marker":request.form["%s.marker" %group],\
                        "markerstyles_col":request.form["%s.markerstyles_col" %group],\
                        "marker_alpha":request.form["%s.marker_alpha" %group],\
                        "markeralpha_col_value":request.form["%s.markeralpha_col_value" %group]
                        }   
                    groups_settings.append(group_dic)
                plot_arguments["groups_settings"]=groups_settings

            for a in list(plot_arguments.keys()):
                if ( a in list(request.form.keys()) ) & ( a not in list(lists.keys())+session["notUpdateList"] ):
                    if a in ["fixed_labels"]:
                        plot_arguments[a]=request.form.getlist(a)
                    else:
                        plot_arguments[a]=request.form[a]
            if "fixed_labels" not in list(request.form.keys()):
                plot_arguments["fixed_labels"]=[]

            # # VALUES SELECTED FROM SELECTION LISTS 
            # # GET UPDATED TO THE LATEST CHOICE
            # for k in list(lists.keys()):
            #     if k in list(request.form.keys()):
            #         plot_arguments[lists[k]]=request.form[k]
            # checkboxes
            for checkbox in session["checkboxes"]:
                if checkbox in list(request.form.keys()) :
                    plot_arguments[checkbox]="on"
                else:
                    try:
                        plot_arguments[checkbox]=request.form[checkbox]
                    except:
                        if plot_arguments[checkbox][0]!=".":
                            plot_arguments[checkbox]="off"


            if plot_arguments["labels_col_value"] != "select a column..":
                df=pd.read_json(session["df"])
                plot_arguments["available_labels"]=list(set( df[ plot_arguments["labels_col_value"] ].tolist() ))

            # UPDATE SESSION VALUES
            session["plot_arguments"]=plot_arguments


        if "df" not in list(session.keys()):
                error_msg="No data to plot, please upload a data or session  file."
                flash(error_msg,'error')
                return render_template('/apps/iscatterplot.html' , filename="Select file..", apps=apps,  **plot_arguments)
 
        #if session["plot_arguments"]["groups_value"]=="None":
        #    session["plot_arguments"]["groups_auto_generate"]=".on"

        # MAKE SURE WE HAVE THE LATEST ARGUMENTS FOR THIS SESSION
        filename=session["filename"]
        plot_arguments=session["plot_arguments"]



        # READ INPUT DATA FROM SESSION JSON
        df=pd.read_json(session["df"])

        #CALL FIGURE FUNCTION
        # try:
        fig=make_figure(df,plot_arguments)
        figure_url = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        return render_template('/apps/iscatterplot.html', figure_url=figure_url, filename=filename, apps=apps, **plot_arguments)

        # except Exception as e:
        #     send_exception_email( user=current_user, eapp="iscatterplot", emsg=e, etime=str(datetime.now()) )
        #     flash(e,'error')
        #     return render_template('/apps/iscatterplot.html', filename=filename, apps=apps, **plot_arguments)

    else:
        if download == "download":
            # READ INPUT DATA FROM SESSION JSON
            df=pd.read_json(session["df"])
            plot_arguments=session["plot_arguments"]

            # CALL FIGURE FUNCTION
            fig=make_figure(df,plot_arguments)

            pio.orca.config.executable='/miniconda/bin/orca'
            pio.orca.config.use_xvfb = True
            #pio.orca.config.save()
            #flash('Figure is being sent to download but will not be updated on your screen.')
            figfile = io.BytesIO()
            mimetypes={"png":'image/png',"pdf":"application/pdf","svg":"image/svg+xml"}

            pa_={}
            for v in ["fig_height","fig_width"]:
                if plot_arguments[v] != "":
                    pa_[v]=False
                elif plot_arguments[v]:
                    pa_[v]=float(plot_arguments[v])
                else:
                    pa_[v]=False

            if (pa_["fig_height"]) & (pa_["fig_width"]):
                fig.write_image( figfile, format=plot_arguments["downloadf"], height=pa_["fig_height"] , width=pa_["fig_width"] )
            else:
                fig.write_image( figfile, format=plot_arguments["downloadf"] )

            figfile.seek(0)  # rewind to beginning of file

            eventlog = UserLogging(email=current_user.email,action="download figure iscatterplot")
            db.session.add(eventlog)
            db.session.commit()

            return send_file(figfile, mimetype=mimetypes[plot_arguments["downloadf"]], as_attachment=True, attachment_filename=plot_arguments["downloadn"]+"."+plot_arguments["downloadf"] )

        if "app" not in list(session.keys()):
            return_to_plot=False
        elif session["app"] != "iscatterplot" :
            return_to_plot=False
        else:
            return_to_plot=True

        if not return_to_plot:
            # INITIATE SESSION
            session["filename"]="Select file.."

            plot_arguments, lists, notUpdateList, checkboxes=figure_defaults()

            session["plot_arguments"]=plot_arguments
            session["lists"]=lists
            session["notUpdateList"]=notUpdateList
            session["COMMIT"]=app.config['COMMIT']
            session["app"]="iscatterplot"
            session["checkboxes"]=checkboxes

        eventlog = UserLogging(email=current_user.email, action="visit iscatterplot")
        db.session.add(eventlog)
        db.session.commit()
        
        return render_template('apps/iscatterplot.html',  filename=session["filename"], apps=apps, **session["plot_arguments"])