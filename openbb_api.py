import json
from datetime import datetime

app = __import__('flask').Flask(__name__)


@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


@app.route('/api/health')
def health():
    return __import__('flask').jsonify({'status': 'ok', 'time': datetime.now().isoformat()})


if __name__ == '__main__':
    app.run(debug=True)
