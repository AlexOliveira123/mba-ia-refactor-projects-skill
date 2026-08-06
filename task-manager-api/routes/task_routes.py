from flask import Blueprint

from controllers import task_controller
from middlewares.auth import require_auth

task_bp = Blueprint('tasks', __name__)


@task_bp.route('/tasks', methods=['GET'])
def get_tasks_route():
    return task_controller.get_tasks()


@task_bp.route('/tasks/<int:task_id>', methods=['GET'])
def get_task_route(task_id):
    return task_controller.get_task(task_id)


@task_bp.route('/tasks', methods=['POST'])
def create_task_route():
    return task_controller.create_task()


@task_bp.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task_route(task_id):
    return task_controller.update_task(task_id)


@task_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@require_auth
def delete_task_route(task_id):
    return task_controller.delete_task(task_id)


@task_bp.route('/tasks/search', methods=['GET'])
def search_tasks_route():
    return task_controller.search_tasks()


@task_bp.route('/tasks/stats', methods=['GET'])
def task_stats_route():
    return task_controller.task_stats()
