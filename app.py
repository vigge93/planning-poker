import functools
from flask import Flask, render_template, request, url_for, redirect, session, flash

from uuid import uuid4, UUID
import os

from dataclasses import dataclass, field

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY') or str(uuid4())
)

@dataclass
class Player():
    username: str

@dataclass
class Task():
    description: str
    votes: dict[str, int] = field(default_factory=dict)

COLORS = ['success', 'danger', 'primary', 'warning', 'info']

CARDS = [(1, 'success'), (2, 'danger'), (3, 'primary'), (5, 'warning'), (8, 'info'), (13, 'success'), (20, 'danger'), (40, 'primary'), (100, 'warning')]

sessions = {}

def session_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if session.get('session', None) is None:
            flash('Session required!')
            return redirect(url_for("index"))
        return view(**kwargs)
    return wrapped_view

def user_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if session.get('username', None) is None:
            flash('You must register!')
            return redirect(url_for("index"))
        return view(**kwargs)
    return wrapped_view

@app.route('/', methods=('GET', ))
def index():
    players = {}
    tasks = []
    cards = []
    sessionTok = session.get('session', None)
    if sessionTok and sessionTok not in sessions:
        sessions[sessionTok] = {'players': {}, 'tasks': [], 'cards': CARDS}
        
    if sessionTok and (username := session.get('username', None)) is not None:
        if username not in sessions[sessionTok]['players']:
            sessions[sessionTok]['players'][username] = Player(username)
    if sessionTok is not None:
        players = sessions[sessionTok]['players']
        tasks = sessions[sessionTok]['tasks']
        cards = sessions[sessionTok]['cards']
    return render_template('index.html', tasks=tasks, players=players, cards=cards)

@app.route('/change_cards', methods=('GET', 'POST'))
@session_required
@user_required
def change_cards():
    if request.method == 'POST':
        cards = request.form.get('cards', '')
        sessions[session['session']]['cards'] = []
        for idx, card in enumerate(cards.split(',')):
            if not card.isnumeric():
                continue
            sessions[session['session']]['cards'].append((card, COLORS[idx % len(COLORS)]))
        return redirect(url_for('index'))
    return render_template('change_cards.html')

@app.route('/create_session')
def create_session():
    sessionTok = uuid4()
    session['session'] = sessionTok
    sessions[sessionTok] = {'players': {}, 'tasks': [], 'cards': CARDS}
    flash(f'New session token: {sessionTok}')
    return redirect(url_for('index'))

@app.route('/join_session', methods=('GET', 'POST'))
def join_session():
    if request.method == 'POST':
        sessionTok = UUID(request.form['session'])
        if sessionTok not in sessions:
            flash('Invalid session token!')
            return render_template('join_session.html')
        session['session'] = sessionTok
        return redirect(url_for('index'))
    return render_template('join_session.html')

@app.route('/stories', methods=('GET', 'POST'))
@session_required
@user_required
def add_stories():    
    if request.method == 'POST':
        tasks_form = request.form.get('tasks', '')
        for task in tasks_form.split('\n'):
            if len(task) == 0 or task.isspace():
                continue
            sessions[session['session']]['tasks'].append(Task(task.strip()))
        return redirect(url_for('index'))
    return render_template('create_tasks.html')

@app.route('/add_player', methods=('GET', 'POST'))
@session_required
def add_player():
    if session.get('username', None) is not None:
        flash('You are already registered!')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        if username.isspace() or username == '':
            flash('Username must not be whitespace only!')
            return render_template('add_user.html')
        session['username'] = username
        sessions[session['session']]['players'][username] = Player(username)
        return redirect(url_for('index'))
    return render_template('add_user.html')
    
@app.route('/start')
@session_required
@user_required
def start():
    tasks = sessions[session['session']]['tasks']
    if len(tasks) == 0:
        flash('No tasks added!')
        return redirect(url_for('index'))
    return redirect(url_for('round', task=0))

@app.route('/round/<int:task>')
@session_required
@user_required
def round(task):
    tasks = sessions[session['session']]['tasks']
    if task >= len(tasks):
        flash("Task index out of range")
        return redirect(url_for('index'))
    return render_template('round.html', task=tasks[task], id=task, cards=sessions[session['session']]['cards'])

@app.route('/vote/<int:task>/<int:points>')
@session_required
@user_required
def vote(task: int, points: int):
    tasks = sessions[session['session']]['tasks']
    if task < 0 or task >= len(tasks):
        flash("Task index out of range")
        return redirect(url_for('index'))
    tasks[task].votes[session['username']] = points
    return redirect(url_for('results', task=task))

@app.route('/results/<int:task>')
@session_required
@user_required
def results(task: int):
    tasks = sessions[session['session']]['tasks']
    if task >= len(tasks):
        flash("Task index out of range")
        return redirect(url_for('index'))
    return render_template('results.html', task=tasks[task], id=task, has_next=((task+1) < len(tasks)))

@app.route('/export')
@session_required
@user_required
def export():
    tasks = sessions[session['session']]['tasks']
    players = sessions[session['session']]['players']
    return {'tasks': tasks, 'players': players}

@app.route('/reset')
def reset():
    if session.get('session', None) is not None:
        del sessions[session['session']]
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0')