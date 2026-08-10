import logging
from datetime import datetime

from flask import jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from database import db
from models.category import Category
from models.task import Task
from models.user import User
from utils.helpers import (
    MAX_TITLE_LENGTH,
    MIN_TITLE_LENGTH,
    VALID_STATUSES,
    parse_date,
)

logger = logging.getLogger('task_manager_api')


def get_tasks():
    tasks = Task.query.options(joinedload(Task.user), joinedload(Task.category)).all()
    result = []
    for t in tasks:
        task_data = t.to_dict()
        task_data['overdue'] = t.is_overdue()
        task_data['user_name'] = t.user.name if t.user else None
        task_data['category_name'] = t.category.name if t.category else None
        result.append(task_data)

    return jsonify(result), 200


def get_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': 'Task não encontrada'}), 404

    data = task.to_dict()
    data['overdue'] = task.is_overdue()
    return jsonify(data), 200


def create_task():
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Dados inválidos'}), 400

    title = data.get('title')
    if not title:
        return jsonify({'error': 'Título é obrigatório'}), 400

    if len(title) < MIN_TITLE_LENGTH:
        return jsonify({'error': 'Título muito curto'}), 400

    if len(title) > MAX_TITLE_LENGTH:
        return jsonify({'error': 'Título muito longo'}), 400

    description = data.get('description', '')
    status = data.get('status', 'pending')
    priority = data.get('priority', 3)
    user_id = data.get('user_id')
    category_id = data.get('category_id')
    due_date = data.get('due_date')
    tags = data.get('tags')

    if status not in VALID_STATUSES:
        return jsonify({'error': 'Status inválido'}), 400

    if priority < 1 or priority > 5:
        return jsonify({'error': 'Prioridade deve ser entre 1 e 5'}), 400

    if user_id:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404

    if category_id:
        cat = Category.query.get(category_id)
        if not cat:
            return jsonify({'error': 'Categoria não encontrada'}), 404

    task = Task()
    task.title = title
    task.description = description
    task.status = status
    task.priority = priority
    task.user_id = user_id
    task.category_id = category_id

    if due_date:
        parsed = parse_date(due_date)
        if not parsed:
            return jsonify({'error': 'Formato de data inválido. Use YYYY-MM-DD'}), 400
        task.due_date = parsed

    if tags:
        if type(tags) == list:
            task.tags = ','.join(tags)
        else:
            task.tags = tags

    try:
        db.session.add(task)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise

    logger.info('Task criada: %s - %s', task.id, task.title)
    return jsonify(task.to_dict()), 201


def update_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': 'Task não encontrada'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Dados inválidos'}), 400

    if 'title' in data:
        if len(data['title']) < MIN_TITLE_LENGTH:
            return jsonify({'error': 'Título muito curto'}), 400
        if len(data['title']) > MAX_TITLE_LENGTH:
            return jsonify({'error': 'Título muito longo'}), 400
        task.title = data['title']

    if 'description' in data:
        task.description = data['description']

    if 'status' in data:
        if data['status'] not in VALID_STATUSES:
            return jsonify({'error': 'Status inválido'}), 400
        task.status = data['status']

    if 'priority' in data:
        if data['priority'] < 1 or data['priority'] > 5:
            return jsonify({'error': 'Prioridade deve ser entre 1 e 5'}), 400
        task.priority = data['priority']

    if 'user_id' in data:
        if data['user_id']:
            user = User.query.get(data['user_id'])
            if not user:
                return jsonify({'error': 'Usuário não encontrado'}), 404
        task.user_id = data['user_id']

    if 'category_id' in data:
        if data['category_id']:
            cat = Category.query.get(data['category_id'])
            if not cat:
                return jsonify({'error': 'Categoria não encontrada'}), 404
        task.category_id = data['category_id']

    if 'due_date' in data:
        if data['due_date']:
            parsed = parse_date(data['due_date'])
            if not parsed:
                return jsonify({'error': 'Formato de data inválido'}), 400
            task.due_date = parsed
        else:
            task.due_date = None

    if 'tags' in data:
        if type(data['tags']) == list:
            task.tags = ','.join(data['tags'])
        else:
            task.tags = data['tags']

    task.updated_at = datetime.utcnow()

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise

    logger.info('Task atualizada: %s', task.id)
    return jsonify(task.to_dict()), 200


def delete_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'error': 'Task não encontrada'}), 404

    try:
        db.session.delete(task)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise

    logger.info('Task deletada: %s', task_id)
    return jsonify({'message': 'Task deletada com sucesso'}), 200


def search_tasks():
    query = request.args.get('q', '')
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    user_id = request.args.get('user_id', '')

    tasks = Task.query

    if query:
        tasks = tasks.filter(
            db.or_(
                Task.title.like(f'%{query}%'),
                Task.description.like(f'%{query}%')
            )
        )

    if status:
        tasks = tasks.filter(Task.status == status)

    if priority:
        tasks = tasks.filter(Task.priority == int(priority))

    if user_id:
        tasks = tasks.filter(Task.user_id == int(user_id))

    results = tasks.all()
    output = [t.to_dict() for t in results]

    return jsonify(output), 200


def task_stats():
    total = Task.query.count()
    pending = Task.query.filter_by(status='pending').count()
    in_progress = Task.query.filter_by(status='in_progress').count()
    done = Task.query.filter_by(status='done').count()
    cancelled = Task.query.filter_by(status='cancelled').count()

    all_tasks = Task.query.all()
    overdue_count = sum(1 for t in all_tasks if t.is_overdue())

    stats = {
        'total': total,
        'pending': pending,
        'in_progress': in_progress,
        'done': done,
        'cancelled': cancelled,
        'overdue': overdue_count,
        'completion_rate': round((done / total) * 100, 2) if total > 0 else 0
    }

    return jsonify(stats), 200
