from website import create_app


app = create_app()

# Debug route to see all registered routes
@app.route('/debug/routes')
def list_routes():
    import urllib.parse
    output = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods)
        line = urllib.parse.unquote(f"{rule.endpoint}: {rule.rule} [{methods}]")
        output.append(line)
    return '<br>'.join(sorted(output))

if __name__ == '__main__':
    app.run(debug=True)