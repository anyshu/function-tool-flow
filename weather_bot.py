import os
from dotenv import load_dotenv
from openai import OpenAI
import json
from flask import Flask, request, jsonify, render_template_string, session
import uuid
from urllib.parse import urljoin

# Load environment variables
load_dotenv()

# Initialize Flask app with subdirectory support
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Get the base URL from environment, ensuring it ends with a slash
API_BASE_URL = os.getenv('API_BASE_URL', '').rstrip('/') + '/'

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_API_BASE")
)

# Default functions definition
DEFAULT_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_temperature",
            "description": "Get the current temperature for a specific location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g., San Francisco, CA"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["Celsius", "Fahrenheit"],
                        "description": "The temperature unit to use"
                    }
                },
                "required": ["location", "unit"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_rain_probability",
            "description": "Get the probability of rain for a specific location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g., San Francisco, CA"
                    }
                },
                "required": ["location"]
            }
        }
    }
]

# HTML template for the landing page with function tools management
LANDING_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Function Tool Tester</title>
    <meta name="api-base-url" content="{{ api_base_url }}">
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        pre {
            background-color: #fff;
            padding: 15px;
            border-radius: 5px;
            white-space: pre-wrap;       /* 保留空格和换行，但允许自动换行 */
            word-wrap: break-word;       /* 允许单词内换行 */
            margin: 0;
        }
        .container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        .left-panel, .right-panel {
            background-color: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            height: fit-content;
        }
        .tools-editor {
            margin-bottom: 20px;
            position: relative;
        }
        textarea {
            width: 100%;
            height: 200px;
            font-family: monospace;
            margin-bottom: 10px;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            resize: none;
            overflow-y: auto;
            line-height: 1.5;
            tab-size: 2;
            white-space: pre-wrap;       /* 保留空格和换行，但允许自动换行 */
            word-wrap: break-word;       /* 允许单词内换行 */
            overflow-x: hidden;          /* 隐藏水平滚动条 */
        }
        button {
            padding: 10px 20px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        button:hover {
            background-color: #45a049;
        }
        .tools-container {
            max-height: 500px;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
            background-color: #fff;
        }
        .tool {
            background-color: #f8f9fa;
            padding: 15px;
            margin: 10px;
            border-radius: 4px;
            border: 1px solid #e9ecef;
        }
        .tool:hover {
            border-color: #4CAF50;
        }
        .response-container {
            margin-top: 20px;
        }
        .model-response, .function-call {
            background-color: #fff;
            padding: 15px;
            border-radius: 4px;
            margin-top: 10px;
            border: 1px solid #ddd;
        }
        .model-response {
            background-color: #e8f5e9;
        }
        .function-call {
            background-color: #fff3e0;
        }
        h1, h2, h3 {
            color: #2c3e50;
            margin-top: 0;
        }
        .scroll-container {
            max-height: calc(100vh - 250px);
            overflow-y: auto;
            padding-right: 10px;
        }
        #updateResult {
            margin-top: 10px;
            padding: 10px;
            border-radius: 4px;
        }
        .success {
            background-color: #e8f5e9;
            color: #2e7d32;
        }
        .error {
            background-color: #ffebee;
            color: #c62828;
        }
        @media (max-width: 768px) {
            .container {
                grid-template-columns: 1fr;
            }
            body {
                padding: 10px;
            }
        }
    </style>
</head>
<body>
    <h1>Function Tool Tester</h1>
    
    <div class="container">
        <div class="left-panel">
            <h2>测试查询</h2>
            <p>发送查询请求，查看模型如何理解和调用函数：</p>
            <textarea id="queryInput" placeholder="输入你的查询，例如：'北京今天的天气怎么样？'"></textarea>
            <button onclick="sendQuery()">发送查询</button>
            <div class="response-container">
                <h3>模型响应：</h3>
                <div id="modelResponse" class="model-response">等待响应...</div>
                <h3>函数调用意图：</h3>
                <div id="functionCalls" class="function-call">等待响应...</div>
            </div>
        </div>
        
        <div class="right-panel">
            <h2>Tools 定义</h2>
            <div class="tools-editor">
                <textarea id="toolsDefinition" placeholder="在此编辑 Tools 定义...">{{ tools_json }}</textarea>
                <button onclick="updateTools()">更新 Tools 定义</button>
                <div id="updateResult"></div>
            </div>
            
            <h2>当前可用的 Tools</h2>
            <div class="scroll-container">
                <div class="tools-container">
                    {% for tool in tools %}
                        <div class="tool">
                            <h3>{{ tool.function.name }}</h3>
                            <p><strong>描述：</strong> {{ tool.function.description }}</p>
                            <p><strong>参数：</strong></p>
                            <pre>{{ tool.function.parameters | tojson(indent=2) }}</pre>
                        </div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>

    <script>
        // API 配置
        const API_CONFIG = {
            baseUrl: document.querySelector('meta[name="api-base-url"]')?.content || window.location.origin,
            endpoints: {
                test: 'api/test',
                updateTools: 'api/update-tools'
            }
        };

        // 统一的 API 调用处理函数
        async function callApi(endpoint, data = null, options = {}) {
            // 确保baseUrl末尾有斜杠
            const baseUrl = API_CONFIG.baseUrl.endsWith('/') ? API_CONFIG.baseUrl : API_CONFIG.baseUrl + '/';
            const url = new URL(API_CONFIG.endpoints[endpoint], baseUrl).toString();
            const defaultOptions = {
                headers: {
                    'Content-Type': 'application/json'
                }
            };

            try {
                const response = await fetch(url, {
                    ...defaultOptions,
                    ...options,
                    ...(data ? { 
                        method: 'POST',
                        body: JSON.stringify(data)
                    } : {})
                });

                const responseData = await response.json();

                if (!response.ok) {
                    throw new Error(responseData.error || '请求失败');
                }

                return responseData;
            } catch (error) {
                console.error(`API调用失败 (${endpoint}):`, error, '请求URL:', url);
                throw error;
            }
        }

        // 初始化配置
        function initializeApi() {
            // 从页面 meta 标签或环境变量中获取配置
            const apiBaseUrl = document.querySelector('meta[name="api-base-url"]')?.content;
            if (apiBaseUrl) {
                API_CONFIG.baseUrl = apiBaseUrl;
            }

            // 记录当前配置
            console.log('API Configuration:', API_CONFIG);
        }

        // 格式化 JSON 并更新文本框
        function formatAndUpdateTools() {
            const toolsDefinition = document.getElementById('toolsDefinition');
            try {
                const toolsData = JSON.parse(toolsDefinition.value);
                const formattedJson = JSON.stringify(toolsData, null, 2);
                
                // 保存当前状态
                const scrollTop = toolsDefinition.scrollTop;
                const selectionStart = toolsDefinition.selectionStart;
                const selectionEnd = toolsDefinition.selectionEnd;
                
                // 更新文本框内容
                toolsDefinition.value = formattedJson;
                
                // 恢复状态
                toolsDefinition.scrollTop = scrollTop;
                toolsDefinition.selectionStart = selectionStart;
                toolsDefinition.selectionEnd = selectionEnd;
            } catch (error) {
                console.error('JSON格式化失败:', error);
            }
        }

        async function sendQuery() {
            const query = document.getElementById('queryInput').value;
            const modelResponse = document.getElementById('modelResponse');
            const functionCalls = document.getElementById('functionCalls');
            
            modelResponse.innerHTML = '处理中...';
            functionCalls.innerHTML = '处理中...';
            
            try {
                const data = await callApi('test', { query });
                modelResponse.innerHTML = `<pre>${data.model_message || '无响应'}</pre>`;
                functionCalls.innerHTML = `<pre>${JSON.stringify(data.function_calls || [], null, 2)}</pre>`;
            } catch (error) {
                modelResponse.innerHTML = `<pre class="error">错误：${error.message}</pre>`;
                functionCalls.innerHTML = `<pre class="error">错误：${error.message}</pre>`;
            }
        }

        async function updateTools() {
            const toolsDefinition = document.getElementById('toolsDefinition');
            const resultElement = document.getElementById('updateResult');
            
            try {
                const toolsData = JSON.parse(toolsDefinition.value);
                
                // 保存当前状态
                const scrollTop = toolsDefinition.scrollTop;
                const selectionStart = toolsDefinition.selectionStart;
                const selectionEnd = toolsDefinition.selectionEnd;
                
                const data = await callApi('updateTools', { tools: toolsData });
                
                resultElement.className = 'success';
                resultElement.textContent = '更新成功！';
                
                // 格式化并更新显示
                const formattedJson = JSON.stringify(toolsData, null, 2);
                toolsDefinition.value = formattedJson;
                
                // 恢复状态
                toolsDefinition.scrollTop = scrollTop;
                toolsDefinition.selectionStart = selectionStart;
                toolsDefinition.selectionEnd = selectionEnd;
                
                // 更新工具列表
                updateToolsList(toolsData);
            } catch (error) {
                resultElement.className = 'error';
                resultElement.textContent = '更新失败：' + error.message;
            }
        }

        // 页面加载时初始化
        document.addEventListener('DOMContentLoaded', function() {
            initializeApi();
            
            // 初始化时格式化 Tools 定义
            formatAndUpdateTools();
            
            const textarea = document.getElementById('toolsDefinition');
            
            // 处理tab键
            textarea.addEventListener('keydown', function(e) {
                if (e.key === 'Tab') {
                    e.preventDefault();
                    const start = this.selectionStart;
                    const end = this.selectionEnd;
                    
                    this.value = this.value.substring(0, start) + '  ' + this.value.substring(end);
                    this.selectionStart = this.selectionEnd = start + 2;
                }
            });
        });

        // 格式化工具列表显示
        function updateToolsList(tools) {
            const container = document.querySelector('.tools-container');
            let html = '';
            
            for (const tool of tools) {
                html += `
                    <div class="tool">
                        <h3>${tool.function.name}</h3>
                        <p><strong>描述：</strong> ${tool.function.description}</p>
                        <p><strong>参数：</strong></p>
                        <pre>${JSON.stringify(tool.function.parameters, null, 2)}</pre>
                    </div>
                `;
            }
            
            container.innerHTML = html;
        }
    </script>
</body>
</html>"""

def get_session_tools():
    """Get tools definition for current session"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    if 'tools' not in session:
        session['tools'] = DEFAULT_FUNCTIONS.copy()
    return session['tools']

def process_function_test(query: str):
    """Process the query and return model's response without executing functions"""
    messages = [
        {"role": "system", "content": "You are a tool bot. Analyze the query and decide which functions to call."},
        {"role": "user", "content": query}
    ]

    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL"),
            messages=messages,
            tools=get_session_tools(),  # 使用会话中的tools定义
            tool_choice="auto"
        )

        assistant_message = response.choices[0].message
        
        # Extract function calls if they exist
        function_calls = []
        if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                function_calls.append({
                    "name": tool_call.function.name,
                    "arguments": json.loads(tool_call.function.arguments)
                })
        
        return {
            "model_message": assistant_message.content,
            "function_calls": function_calls
        }
    except Exception as e:
        raise

@app.route('/')
def index():
    """Landing page with API documentation"""
    # 确保在渲染页面时提供格式化好的 JSON
    tools = get_session_tools()
    formatted_json = json.dumps(tools, indent=2)
    
    return render_template_string(
        LANDING_PAGE_HTML,
        tools=tools,
        tools_json=formatted_json,
        api_base_url=API_BASE_URL
    )

@app.route('/api/test', methods=['POST'])
def test_function_calls():
    """API endpoint for testing function calls"""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 415
    
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({'error': 'No query provided in request body'}), 400
    
    if not isinstance(data['query'], str):
        return jsonify({'error': 'Query must be a string'}), 400
    
    try:
        response = process_function_test(data['query'])
        return jsonify(response)
    except Exception as e:
        app.logger.error(f"Error processing query: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/update-tools', methods=['POST'])
def update_tools():
    """API endpoint for updating tools definition"""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 415
    
    data = request.get_json()
    if not data or 'tools' not in data:
        return jsonify({'error': 'No tools definition provided'}), 400
    
    try:
        # Validate the tools definition structure
        new_tools = data['tools']
        for tool in new_tools:
            if not isinstance(tool, dict) or 'type' not in tool or 'function' not in tool:
                return jsonify({'error': 'Invalid tool definition structure'}), 400
        
        # 更新会话中的tools定义
        session['tools'] = new_tools
        return jsonify({'message': 'Tools updated successfully'})
    except Exception as e:
        app.logger.error(f"Error updating tools: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({'error': 'The requested resource was not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == "__main__":
    print(f"API Base URL: {API_BASE_URL}")
    app.run(host='0.0.0.0', port=5001, debug=True)