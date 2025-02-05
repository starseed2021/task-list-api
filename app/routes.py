from types import new_class 
import requests
from app import db
from flask import Blueprint, jsonify, request
from app.models.task import Task
from app.models.goal import Goal
from datetime import datetime
import os


tasks_bp = Blueprint("tasks_bp", __name__, url_prefix="/tasks")

@tasks_bp.route("", methods=["POST", "GET"])
def handle_tasks():
    # POST REQUESTS
    if request.method == "POST":

        request_body = request.get_json()
        if "title" not in request_body or "description" not in request_body or "completed_at" not in request_body:
            
            return jsonify({"details": "Invalid data"}), 400

        new_task = Task(
            title = request_body["title"],
            description = request_body["description"]
        )
        if "completed_at" in request_body:
            new_task.completed_at = request_body["completed_at"]


        db.session.add(new_task)
        db.session.commit()

        new_task_response = { 
            "task": new_task.get_task_dict()
        }

        return jsonify(new_task_response), 201

    # GET REQUESTS
    elif request.method == "GET":
        title_query = request.args.get("title")
        description_query = request.args.get("description")
        if title_query:
            tasks = Task.query.filter(Task.title.contains(title_query))
        elif description_query:
            tasks = Task.query.filter(Task.description.contains(description_query))
        else:
            tasks = Task.query.all()

        # QUERY PARAMS (Ascending and Descending Order by Title)
        sort_query = request.args.get("sort")
        if sort_query == "asc":
            tasks = Task.query.order_by(Task.title.asc())
        elif sort_query == "desc":
            tasks = Task.query.order_by(Task.title.desc()) 
        else:
            tasks = Task.query.all()

        task_response = []
        for task in tasks:
            task_response.append(task.get_task_dict())
            
        if task_response == []:
            return jsonify(task_response), 200

        return jsonify(task_response), 200

# GET, PUT, DELETE ONE AT A TIME
@tasks_bp.route("/<task_id>", methods=["GET", "PUT", "DELETE"])
def handle_one_task_at_a_time(task_id):
    task = Task.query.get(task_id)
    if task is None:
        return jsonify(None), 404
    
    if request.method == "GET":
        return {
            "task": task.get_task_dict()
        }, 20

    elif request.method == "PUT":
    
        request_body = request.get_json()

        task.title = request_body["title"]
        task.description = request_body["description"]

        db.session.commit()

        updated_task_response = {
            "task": task.get_task_dict()
            }

        return jsonify(updated_task_response), 200

    elif request.method == "DELETE":
    
        db.session.delete(task)
        db.session.commit()

        delete_response = {"details": (f'Task {task_id} "{task.title}" successfully deleted')}

        return jsonify(delete_response), 200

# PATCH REQUESTS as either complete or not complete
# endpoints are expressed w/out carrots for search specificity
@tasks_bp.route("/<task_id>/mark_complete", methods=["PATCH"])
def handle_tasks_complete(task_id):
    task = Task.query.get(task_id)
    if task is None:
        return jsonify(None), 404

    # setting the completed_at with a datetime
    task.completed_at = datetime.utcnow()
    db.session.commit()

    # Send Slack Message Using Slack API
    slack_url = "https://slack.com/api/chat.postMessage"
    bearer_token = os.environ.get("BEARER_TOKEN")
    slack_channel = 'slack-api-test-channel'
    text = f'Someone just completed the task {task.title}'
    slack_user_name = "Starseed's Bot"

    requests.patch(slack_url, data={
        'token': bearer_token,
        'channel': slack_channel,
        'text': text,
        'username': slack_user_name,}).json()

    updated_task_response =  {
            "task": task.get_task_dict()
            }
    
    return jsonify(updated_task_response), 200

@tasks_bp.route("/<task_id>/mark_incomplete", methods=["PATCH"])
def handle_tasks_not_complete(task_id):
    task = Task.query.get(task_id)
    if task is None:
        return jsonify(None), 404

    # setting the completed_at to None
    task.completed_at = None
    db.session.commit()

    updated_task_response =  {
            "task": task.get_task_dict()
        }
    return jsonify(updated_task_response), 200

goals_bp = Blueprint("goals_bp", __name__, url_prefix="/goals")

@goals_bp.route("", methods=["POST", "GET"])
def handle_goals():
    #POST REQUESTS
    if request.method == "POST":
        goal_request_body = request.get_json()
        if "title" not in goal_request_body:
            return jsonify({"details": "Invalid data"}), 400
        
        new_goal = Goal(title = goal_request_body["title"])

        db.session.add(new_goal)
        db.session.commit()

        new_goal_response = {
            "goal": new_goal.get_goal_dict()
        }

        return jsonify(new_goal_response), 201

    #GET REQUESTS
    elif request.method == "GET":
        goal_title_query = request.args.get("title")
        if goal_title_query:
            goals = Goal.query.filter(Goal.title.contains(goal_title_query))
        else:
            goals = Goal.query.all()

        goal_response = []
        for goal in goals:
            goal_response.append(goal.get_goal_dict())

        if goal_response == []:
            return jsonify(goal_response), 200

        return jsonify(goal_response), 200

@goals_bp.route("/<goal_id>", methods=["GET", "PUT", "DELETE"])
def handle_one_goal_at_time(goal_id):
    # GET & POST REQUEST; ONE TO MANY RELATIONSHIP
    goal = Goal.query.get(goal_id)
    if goal is None:
        return jsonify(None), 404
    if request.method == "GET":
        return {
            "goal": goal.get_goal_dict()
        }, 200


    elif request.method == "PUT":
        goal = Goal.query.get(goal_id)
        goal_request_body = request.get_json()

        goal.title = goal_request_body["title"]

        db.session.commit()

        updated_goal_response = {
            "goal": goal.get_goal_dict()
        }

        return jsonify(updated_goal_response), 200 

    elif request.method == "DELETE":

        db.session.delete(goal)
        db.session.commit()

        goal_delete_response = {'details': (f'Goal {goal_id} "{goal.title}" successfully deleted')}
        return jsonify(goal_delete_response), 200

@goals_bp.route("/<goal_id>/tasks", methods=["POST", "GET"])
def handle_goals_tasks(goal_id):
    goal = Goal.query.get(goal_id)
    if goal is None:
        return jsonify(None), 404
    
    if request.method == "POST":    
        request_body = request.get_json()

        tasks = []
        for task_id in request_body["task_ids"]:
            tasks.append(Task.query.get(task_id))

        goal.tasks = tasks

        db.session.commit()

        task_ids = []
        for task in goal.tasks:
            task_ids.append(task.id)

        goal_tasks_response = {goal.get_goal_dict()}

        return jsonify(goal_tasks_response), 200

    elif request.method == "GET":
        tasks = []
        for task in goal.tasks:
            tasks.append(task.get_task_dict())
        

        goal_response = {
            "id": goal.goal_id,
            "title": goal.title,
            "tasks": tasks
        }

        return jsonify(goal_response), 200








