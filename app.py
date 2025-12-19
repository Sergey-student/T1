import dash
from dash import dcc, html, dash_table, Input, Output, State, callback
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import base64
import io

# Инициализация приложения
app = dash.Dash(__name__)
server = app.server

app.layout = html.Div([
    # Заголовок
    html.H1("🚀 Анализ процесса разработки ПО", 
            style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '30px'}),
    
    # Загрузка файла
    html.Div([
        dcc.Upload(
            id='upload-data',
            children=html.Div([
                '📁 Перетащите или ',
                html.A('выберите CSV файл')
            ]),
            style={
                'width': '100%', 'height': '60px', 'lineHeight': '60px',
                'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
                'textAlign': 'center', 'margin': '10px'
            },
            multiple=False
        ),
    ], style={'width': '50%', 'margin': 'auto'}),
    
    # Выбор периода
    html.Div([
        html.Label("📅 Выберите период анализа:", style={'fontWeight': 'bold'}),
        dcc.Dropdown(
            id='period-selector',
            options=[
                {'label': 'Спринт (2 недели)', 'value': 'sprint'},
                {'label': 'Неделя', 'value': 'week'},
                {'label': 'Месяц', 'value': 'month'}
            ],
            value='sprint',
            style={'width': '250px', 'margin': '10px'}
        )
    ], style={'margin': '20px'}),
    
    # Индикаторы метрик разработки
    html.Div([
        html.Div([
            html.H4("0", id='velocity'),
            html.P("Velocity (story points)")
        ], className='indicator', style={'padding': '20px', 'background': '#e8f5e9', 'borderRadius': '10px', 'textAlign': 'center'}),
        
        html.Div([
            html.H4("0%", id='completion-rate'),
            html.P("Completion Rate")
        ], className='indicator', style={'padding': '20px', 'background': '#e3f2fd', 'borderRadius': '10px', 'textAlign': 'center'}),
        
        html.Div([
            html.H4("0", id='active-bugs'),
            html.P("Active Bugs")
        ], className='indicator', style={'padding': '20px', 'background': '#fff3e0', 'borderRadius': '10px', 'textAlign': 'center'}),
        
        html.Div([
            html.H4("0%", id='test-coverage'),
            html.P("Test Coverage")
        ], className='indicator', style={'padding': '20px', 'background': '#f3e5f5', 'borderRadius': '10px', 'textAlign': 'center'})
    ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(4, 1fr)', 'gap': '20px', 'margin': '20px'}),
    
    # Графики
    html.Div([
        # 1. Линейный график - динамика velocity и закрытых задач
        dcc.Graph(id='development-trend', style={'gridColumn': 'span 2'}),
        
        # 2. Круговая диаграмма - распределение задач по статусам
        dcc.Graph(id='tasks-distribution'),
        
        # 3. Гистограмма - распределение story points
        dcc.Graph(id='storypoints-histogram', style={'gridColumn': 'span 2'}),
        
        # 4. Точечная диаграмма - корреляция сложности и времени выполнения
        dcc.Graph(id='complexity-correlation')
    ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(2, 1fr)', 'gap': '20px', 'margin': '20px'}),
    
    # Таблица с метриками разработки
    html.Div([
        html.H3("📋 Детальная информация по задачам"),
        dash_table.DataTable(
            id='dev-metrics-table',
            page_size=10,
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '10px'},
            style_header={'backgroundColor': '#2c3e50', 'color': 'white', 'fontWeight': 'bold'}
        )
    ], style={'margin': '20px'}),
    
    # Отображение ошибок
    html.Div(id='error-message', style={'color': 'red', 'margin': '20px'})
], style={'fontFamily': 'Arial, sans-serif', 'padding': '20px'})

# Callback для обработки загруженного файла
@app.callback(
    [Output('development-trend', 'figure'),
     Output('tasks-distribution', 'figure'),
     Output('storypoints-histogram', 'figure'),
     Output('complexity-correlation', 'figure'),
     Output('dev-metrics-table', 'data'),
     Output('dev-metrics-table', 'columns'),
     Output('velocity', 'children'),
     Output('completion-rate', 'children'),
     Output('active-bugs', 'children'),
     Output('test-coverage', 'children'),
     Output('error-message', 'children')],
    [Input('upload-data', 'contents'),
     Input('period-selector', 'value')],
    [State('upload-data', 'filename'),
     State('upload-data', 'last_modified')]
)
def update_dashboard(contents, period, filename, last_modified):
    # Инициализация пустых фигур по умолчанию
    empty_fig = go.Figure()
    empty_fig.update_layout(
        title="Загрузите CSV файл для отображения данных",
        xaxis_title="",
        yaxis_title="",
        annotations=[
            dict(
                text="Нет данных",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False
            )
        ]
    )
    
    # Возвращаем значения по умолчанию если файл не загружен
    if contents is None:
        return [empty_fig, empty_fig, empty_fig, empty_fig, 
                [], [], "0", "0%", "0", "0%", "Ожидание загрузки файла..."]
    
    try:
        # Обработка загруженного файла
        content_type, content_string = contents.split(',')
        
        # Декодирование base64
        decoded = base64.b64decode(content_string)
        
        # Пробуем разные кодировки
        try:
            decoded_str = decoded.decode('utf-8')
        except UnicodeDecodeError:
            try:
                decoded_str = decoded.decode('cp1251')
            except:
                decoded_str = decoded.decode('latin-1')
        
        # Чтение CSV
        df = pd.read_csv(io.StringIO(decoded_str))
        
        # Проверяем обязательные колонки
        required_columns = ['date']
        if not all(col in df.columns for col in required_columns):
            error_msg = f"Файл должен содержать колонку: {required_columns}"
            return [empty_fig, empty_fig, empty_fig, empty_fig, 
                    [], [], "0", "0%", "0", "0%", error_msg]
        
        # Преобразование данных
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # Удаляем строки с некорректными датами
        df = df.dropna(subset=['date'])
        
        # Создание периодов для агрегации
        if period == 'sprint':
            # Создаем спринты по 2 недели
            df['week_number'] = df['date'].dt.isocalendar().week
            df['sprint'] = (df['week_number'] // 2).astype(str)
            period_col = 'sprint'
        elif period == 'week':
            df['week'] = df['date'].dt.isocalendar().week.astype(str)
            period_col = 'week'
        else:
            df['month'] = df['date'].dt.strftime('%Y-%m')
            period_col = 'month'
        
        # Расчет дополнительных метрик
        if 'task_status' in df.columns:
            df['is_completed'] = df['task_status'].isin(['Done', 'Closed', 'Completed', 'Resolved'])
        
        # Создание графиков
        
        # 1. Линейный график динамики метрик разработки
        trend_fig = go.Figure()
        
        # Добавляем линии для velocity (если есть story_points)
        if 'story_points' in df.columns and 'is_completed' in df.columns:
            completed_tasks = df[df['is_completed'] == True]
            if not completed_tasks.empty:
                velocity_data = completed_tasks.groupby(period_col)['story_points'].sum().reset_index()
                trend_fig.add_trace(go.Scatter(
                    x=velocity_data[period_col],
                    y=velocity_data['story_points'],
                    mode='lines+markers',
                    name='Velocity',
                    line=dict(color='#4CAF50', width=3)
                ))
        
        # Добавляем линию для закрытых задач
        if 'task_status' in df.columns:
            completed_counts = df[df['task_status'].isin(['Done', 'Closed', 'Completed', 'Resolved'])].groupby(period_col).size().reset_index(name='completed_tasks')
            if not completed_counts.empty:
                trend_fig.add_trace(go.Scatter(
                    x=completed_counts[period_col],
                    y=completed_counts['completed_tasks'],
                    mode='lines+markers',
                    name='Завершенные задачи',
                    line=dict(color='#2196F3', width=3)
                ))
        
        # Добавляем линию для багов
        if 'bugs_found' in df.columns:
            bugs_data = df.groupby(period_col)['bugs_found'].sum().reset_index()
            if not bugs_data.empty:
                trend_fig.add_trace(go.Scatter(
                    x=bugs_data[period_col],
                    y=bugs_data['bugs_found'],
                    mode='lines+markers',
                    name='Найдено багов',
                    line=dict(color='#FF5722', width=3)
                ))
        
        # Если нет данных для графика
        if len(trend_fig.data) == 0:
            trend_fig.add_trace(go.Scatter(
                x=[], y=[], mode='markers',
                name='Нет данных'
            ))
        
        trend_fig.update_layout(
            title='📈 Динамика метрик разработки',
            xaxis_title='Период',
            yaxis_title='Количество',
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        # 2. Круговая диаграмма распределения задач
        if 'task_status' in df.columns:
            status_distribution = df['task_status'].value_counts().reset_index()
            status_distribution.columns = ['status', 'count']
            
            if not status_distribution.empty:
                pie_fig = px.pie(
                    status_distribution,
                    values='count',
                    names='status',
                    title='🥧 Распределение задач по статусам',
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                pie_fig.update_traces(textposition='inside', textinfo='percent+label')
            else:
                pie_fig = empty_fig
                pie_fig.update_layout(title="Нет данных о статусах задач")
        else:
            pie_fig = empty_fig
            pie_fig.update_layout(title="Колонка 'task_status' не найдена")
        
        # 3. Гистограмма распределения story points
        if 'story_points' in df.columns:
            hist_fig = px.histogram(
                df,
                x='story_points',
                nbins=10,
                title='📊 Распределение story points по задачам',
                labels={'story_points': 'Story Points', 'count': 'Количество задач'},
                color_discrete_sequence=['#9C27B0']
            )
            hist_fig.update_layout(bargap=0.1)
        else:
            hist_fig = empty_fig
            hist_fig.update_layout(title="Колонка 'story_points' не найдена")
        
        # 4. Точечная диаграмма корреляции
        if 'story_points' in df.columns and 'actual_hours' in df.columns:
            scatter_fig = px.scatter(
                df,
                x='story_points',
                y='actual_hours',
                color='complexity' if 'complexity' in df.columns else None,
                size='bugs_found' if 'bugs_found' in df.columns else None,
                title='🔍 Корреляция сложности и времени выполнения',
                labels={'story_points': 'Story Points', 'actual_hours': 'Фактические часы'}
            )
            # Добавляем линию тренда вручную без statsmodels
            try:
                # Рассчитываем линейную регрессию
                x = df['story_points'].dropna()
                y = df['actual_hours'].dropna()
                if len(x) > 1 and len(y) > 1:
                    # Используем numpy для простой линейной регрессии
                    import numpy as np
                    z = np.polyfit(x, y, 1)
                    p = np.poly1d(z)
                    
                    # Добавляем линию тренда
                    x_trend = np.linspace(x.min(), x.max(), 100)
                    scatter_fig.add_trace(go.Scatter(
                        x=x_trend,
                        y=p(x_trend),
                        mode='lines',
                        name='Линия тренда',
                        line=dict(color='red', dash='dash')
                    ))
            except:
                pass  # Если не получается добавить линию тренда, просто оставляем без нее
                
        elif 'estimated_hours' in df.columns and 'actual_hours' in df.columns:
            scatter_fig = px.scatter(
                df,
                x='estimated_hours',
                y='actual_hours',
                color='developer' if 'developer' in df.columns else None,
                title='🔍 Корреляция оценки и фактического времени',
                labels={'estimated_hours': 'Оценка (часы)', 'actual_hours': 'Факт (часы)'}
            )
            # Добавляем линию тренда вручную
            try:
                x = df['estimated_hours'].dropna()
                y = df['actual_hours'].dropna()
                if len(x) > 1 and len(y) > 1:
                    import numpy as np
                    z = np.polyfit(x, y, 1)
                    p = np.poly1d(z)
                    
                    x_trend = np.linspace(x.min(), x.max(), 100)
                    scatter_fig.add_trace(go.Scatter(
                        x=x_trend,
                        y=p(x_trend),
                        mode='lines',
                        name='Линия тренда',
                        line=dict(color='red', dash='dash')
                    ))
            except:
                pass
        else:
            scatter_fig = empty_fig
            scatter_fig.update_layout(title="Нет данных для анализа корреляции")
        
        # Подготовка данных для таблицы
        table_data = df.to_dict('records')
        table_columns = [{'name': col, 'id': col} for col in df.columns]
        
        # Расчет метрик разработки
        
        # Velocity (средняя сумма story points за период)
        if 'story_points' in df.columns and period_col in df.columns and 'is_completed' in df.columns:
            completed_df = df[df['is_completed'] == True]
            if not completed_df.empty:
                velocity_value = completed_df.groupby(period_col)['story_points'].sum().mean()
                velocity = f"{velocity_value:.1f}"
            else:
                velocity = "0"
        else:
            velocity = "0"
        
        # Completion Rate (процент завершенных задач)
        if 'task_status' in df.columns:
            total_tasks = len(df)
            completed_tasks = len(df[df['task_status'].isin(['Done', 'Closed', 'Completed', 'Resolved'])])
            completion_rate_value = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            completion_rate = f"{completion_rate_value:.1f}%"
        else:
            completion_rate = "0%"
        
        # Active Bugs (активные баги)
        if 'bugs_found' in df.columns and 'bugs_resolved' in df.columns:
            active_bugs_value = df['bugs_found'].sum() - df['bugs_resolved'].sum()
            active_bugs = f"{max(active_bugs_value, 0)}"
        elif 'active_bugs' in df.columns:
            active_bugs_value = df['active_bugs'].sum()
            active_bugs = f"{active_bugs_value}"
        else:
            active_bugs = "0"
        
        # Test Coverage (покрытие тестами)
        if 'test_coverage' in df.columns:
            test_coverage_value = df['test_coverage'].mean()
            test_coverage = f"{test_coverage_value:.1f}%"
        else:
            test_coverage = "0%"
        
        error_message = f"Файл успешно загружен: {filename}. Записей: {len(df)}"
        
        return [trend_fig, pie_fig, hist_fig, scatter_fig, 
                table_data, table_columns, 
                velocity, completion_rate, active_bugs, test_coverage,
                error_message]
    
    except Exception as e:
        error_msg = f"Ошибка при обработке файла: {str(e)}"
        print(f"Error: {e}")  # Для отладки
        return [empty_fig, empty_fig, empty_fig, empty_fig, 
                [], [], "0", "0%", "0", "0%", error_msg]

if __name__ == '__main__':
    app.run(
        debug=True,
        dev_tools_hot_reload=True,
        dev_tools_ui=True,
        dev_tools_props_check=True
    )
