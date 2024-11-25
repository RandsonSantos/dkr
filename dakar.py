import logging
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
import json
from datetime import datetime
from datetime import timedelta
from flask import session


logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

USERS_FILE = 'json/users.json'
AGENDAMENTOS_FILE = 'json/agendamentos.json'

def load_json(filename):
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def save_json(data, filename):
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)

def load_users():
    users_list = load_json(USERS_FILE)
    users_dict = {str(user['id']): user for user in users_list}
    return users_dict

def save_users(users):
    save_json(list(users.values()), USERS_FILE)

def load_agendamentos():
    return load_json(AGENDAMENTOS_FILE)

def save_agendamentos(agendamentos):
    save_json(agendamentos, AGENDAMENTOS_FILE)

users = load_users()

class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id

    @staticmethod
    def get(user_id):
        user_data = users.get(str(user_id))
        if user_data:
            return User(user_id=user_data['id'])
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(int(user_id))

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=1)  # Tempo de expiração de sessão

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=1)
    
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        logging.debug(f'Tentativa de login: {username}')
        user = next((u for u in users.values() if u['username'] == username), None)
        if user and user['password'] == password:
            user_obj = User(user['id'])
            login_user(user_obj)
            logging.debug(f'Login bem-sucedido para o usuário: {username}')
            flash('Login realizado com sucesso!', 'success')
            next_page = request.args.get('next')
            if not next_page or next_page == 'None':
                next_page = url_for('menu')
            return redirect(next_page)
        else:
            logging.debug(f'Falha no login para o usuário: {username}')
            flash('Credenciais inválidas. Tente novamente.', 'danger')
    return render_template('login.html')

@app.route('/menu')
@login_required
def menu():
    return render_template('menu.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users:
            flash('Usuário já existe. Tente um nome de usuário diferente.', 'danger')
        else:
            user_id = len(users) + 1
            users[username] = {
                'id': user_id,
                'username': username,
                'password': password
            }
            save_users(users)
            flash('Usuário registrado com sucesso!', 'success')
            return redirect(url_for('usuarios'))
    return render_template('register.html')

@app.route('/solicitar_agendamento', methods=['POST'])
def solicitar_agendamento():
    nome = request.form['nome']
    telefone = request.form['telefone']
    placa = request.form['placa']
    tipo_lavagem = request.form['tipo_lavagem']
    opcoes_servicos = request.form.getlist('opcoes_servicos')

    agendamentos = load_agendamentos()
    novo_agendamento = {
        'id': len(agendamentos) + 1,
        'nome': nome,
        'telefone': telefone,
        'placa': placa,
        'tipo_lavagem': tipo_lavagem,
        'opcoes_servicos': ', '.join(opcoes_servicos),
        'data': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'Pendente'
    }
    agendamentos.append(novo_agendamento)
    save_agendamentos(agendamentos)

    flash('Agendamento solicitado com sucesso!', 'success')
    return redirect(url_for('solicitacao_confirmada'))

@app.route('/solicitacao_confirmada')
def solicitacao_confirmada():
    return render_template('solicitacao_confirmada.html')

@app.route('/agenda')
def agenda():
    agendamentos = load_agendamentos()
    data_hoje = datetime.now().strftime('%Y-%m-%d')
    agendamentos_hoje = [ag for ag in agendamentos if ag['data'].startswith(data_hoje)]
    return render_template('agenda.html', agendamentos=agendamentos_hoje)

@app.route('/ver_agendamentos')
@login_required
def ver_agendamentos():
    agendamentos = load_agendamentos()
    return render_template('agendamentos.html', agendamentos=agendamentos)

@app.route('/editar_agendamento/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_agendamento(id):
    agendamentos = load_agendamentos()
    agendamento = next((ag for ag in agendamentos if ag['id'] == id), None)

    if not agendamento:
        flash('Agendamento não encontrado.', 'danger')
        return redirect(url_for('ver_agendamentos'))

    if request.method == 'POST':
        agendamento['nome'] = request.form['nome']
        agendamento['telefone'] = request.form['telefone']
        agendamento['placa'] = request.form['placa']
        agendamento['tipo_lavagem'] = request.form['tipo_lavagem']
        opcoes_servicos_selecionados = request.form.getlist('opcoes_servicos')
        agendamento['opcoes_servicos'] = ", ".join(opcoes_servicos_selecionados)
        agendamento['data'] = request.form['data']
        agendamento['status'] = request.form['status']

        save_agendamentos(agendamentos)
        flash('Agendamento atualizado com sucesso!', 'success')
        return redirect(url_for('ver_agendamentos'))

    return render_template('editar_agendamento.html', agendamento=agendamento)

@app.route('/ver_pedido/<int:id>')
@login_required
def ver_pedido(id):
    agendamentos = load_agendamentos()
    agendamento = next((ag for ag in agendamentos if ag['id'] == id), None)

    if not agendamento:
        flash('Agendamento não encontrado.', 'danger')
        return redirect(url_for('ver_agendamentos'))

    return render_template('ver_pedido.html', agendamento=agendamento)

@app.route('/aceitar_agendamento/<int:id>', methods=['POST'])
@login_required
def aceitar_agendamento(id):
    agendamentos = load_agendamentos()
    agendamento = next((ag for ag in agendamentos if ag['id'] == id), None)

    if agendamento:
        agendamento['status'] = 'Aceito'
        save_agendamentos(agendamentos)
        flash('Agendamento aceito com sucesso!', 'success')
    else:
        flash('Agendamento não encontrado.', 'danger')

    return redirect(url_for('ver_pedido', id=id))

@app.route('/atualizar_status_agendamento/<int:id>/<string:status>', methods=['POST'])
@login_required
def atualizar_status_agendamento(id, status):
    agendamentos = load_agendamentos()
    agendamento = next((ag for ag in agendamentos if ag['id'] == id), None)

    if agendamento:
        agendamento['status'] = status
        save_agendamentos(agendamentos)
        flash(f'Agendamento {status.lower()} com sucesso!', 'success')
    else:
        flash('Agendamento não encontrado.', 'danger')

    return redirect(url_for('ver_agendamentos'))

@app.route('/usuarios')
def usuarios():
    return render_template('usuarios.html', users=users.values())

@app.route('/editar_usuario/<int:id>', methods=['GET', 'POST'])
def editar_usuario(id):
    user = users.get(str(id))
    if user is None:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('usuarios'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user['username'] = username
        user['password'] = password
        save_users(users)
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('usuarios'))
    return render_template('editar_usuario.html', user=user)

@app.route('/excluir_usuario/<int:id>', methods=['GET', 'POST'])
def excluir_usuario(id):
    user = users.get(str(id))
    if request.method == 'POST':
        if user:
            users.pop(str(id), None)
            save_users(users)
            flash('Usuário excluído com sucesso!', 'success')
        else:
            flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('usuarios'))
    return render_template('excluir_usuario.html', user=user)

@app.route('/relatorios', methods=['GET', 'POST'])
@login_required
def relatorios():
    clientes = {ag['nome'] for ag in load_agendamentos()}
    placas = {ag['placa'] for ag in load_agendamentos()}
    mes_atual = datetime.now().strftime('%Y-%m')

    return render_template('relatorios.html', clientes=clientes, placas=placas, mes_atual=mes_atual)

@app.route('/resultados', methods=['GET', 'POST'])
@login_required
def resultados():
    if request.method == 'POST':
        agendamentos = load_agendamentos()
        cliente_filtro = request.form.get('cliente').lower()
        placa_filtro = request.form.get('placa').replace("-", "").lower()
        mes_filtro = request.form.get('mes')
        status_filtros = request.form.getlist('status')

        # Filtragem dos agendamentos
        agendamentos_filtrados = [
            ag for ag in agendamentos 
            if (cliente_filtro in ['', ag['nome'].lower()[:len(cliente_filtro)]]) and 
               (placa_filtro in ['', ag['placa'].replace("-", "").lower()[:len(placa_filtro)]]) and
               (mes_filtro in ['', ag['data'][:7]]) and
               (not status_filtros or ag['status'] in status_filtros)
        ]

        return render_template('resultados.html', agendamentos_filtrados=agendamentos_filtrados)
    else:
        return redirect(url_for('relatorios'))

@app.route('/resultados/impressao', methods=['POST'])
def resultados_impressao():
    agendamentos = load_agendamentos()
    cliente_filtro = request.form.get('cliente').lower()
    placa_filtro = request.form.get('placa').replace("-", "").lower()
    status_filtros = request.form.getlist('status')

    # Filtragem dos agendamentos
    agendamentos_filtrados = [
        ag for ag in agendamentos 
        if (cliente_filtro in ['', ag['nome'].lower()[:len(cliente_filtro)]]) and 
           (placa_filtro in ['', ag['placa'].replace("-", "").lower()[:len(placa_filtro)]]) and 
           (not status_filtros or ag['status'] in status_filtros)
    ]

    return render_template('resultados_impressao.html', agendamentos_filtrados=agendamentos_filtrados)

if __name__ == '__main__':
    app.run(debug=True)
