from flask import Flask, render_template, request, jsonify
from rag import rag_inference, DB_CFG

app = Flask(__name__, static_url_path='/static')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    data   = request.get_json()
    query  = data.get('query', '').strip()
    domain = data.get('domain', 'sop')

    if not query:
        return jsonify({"error": "Empty query."}), 400
    if domain not in DB_CFG:
        return jsonify({"error": f"Unknown domain '{domain}'."}), 400

    try:
        answer, sources = rag_inference(domain, query)
        return jsonify({"answer": answer, "sources": sources})
    except Exception as e:
        # Log the error for server-side debugging
        app.logger.exception("Search processing failed")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False)