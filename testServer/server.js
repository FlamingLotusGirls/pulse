
var express = require('express');
var app = express();
var child_process = require('child_process');
var toString = require('stream-to-string');
var log = require('./log.js');

app.get('/', (req, res) => res.send("Hello, World"));

function runCmd(cmd, ...args) {
    return new Promise((accept, reject) => {
	log.info("Running %s, %j", cmd, args)
	let proc = child_process.execFile(cmd, args);
	proc.stdout.on('error', e => {
	    log.error("IO Error: , %s", e.stack);
	    reject(e);
	});
	let out = toString(proc.stdout);
	proc
	    .on('error', reject)
	    .on('exit', (code, signal) => {
		if (code === 0) {
		    log.info("Status %s, %j = %d", cmd, args, code)
		    accept(out);
		} else if (signal) {
		    log.error("Signal %s, %j = %s", cmd, args, signal)
		    reject(new Error(signal));
		} else {
		    log.error("Signal %s, %j = %d", cmd, args, code)
		    reject(new Error(cmd + " Exited with code " + code));
		}
	    });
    })
}

function sendErr(res) {
    return err => res.sendStatus(503, err.stack);
}

function sendText(res) {
    return txt => res.end(txt, "UTF-8");
}

function sendJson(res) {
    return json => res.json(json);
}

app.get('/ls/txt', (req, res) => {
    runCmd('/bin/ls', '-l', req.query.dir || ".")
	.then(sendText(res), sendErr(res));
});

// Example:
// http://localhost:8081/ls/json?dir=/Users/hiromi
app.get('/ls/json', (req, res) => {
    runCmd('/bin/ls', '-l', req.query.dir || ".")
	.then(x => ({status: "OK", result: x.split(/\n+/g)}))
	.catch(err => ({status: "ERROR", message: err.message}))
        .then(sendJson(res), sendErr(res));
});

// Our test system state
var PARAMS = {
    slider1: 5,
    slider2: 30
};

// Do a PUT request to:
// http://localhost:8081/val?param=slider1&value=5
// We use PUT to set, GET to get
app.put('/val', (req, res) => {
    // Get the supplied query parameters
    let param = req.query.param
    let value = Number(req.query.value);
    log.info("Set %s to %d", param, value);
    PARAMS[param] = value
    res.send({status: "OK", param: param, value: value});
});

// Do a GET request to:
// http://localhost:8081/val?param=slider1
// We use PUT to set, GET to get
app.get('/val', (req, res) => {
    // Get the supplied query parameters
    let param = req.query.param
    let value = PARAMS[param];
    if (value === undefined) {
	return res.send({status: "ERROR", message: "Parameter " + param + " is not set.", param: param});
    }
    log.info("Set %s to %d", param, value);
    res.send({status: "OK", param: param, value: value});
});

// Send files in the params/ subdirectory. Use ".json" for json files, .txt for text files.
// http://localhost:8081/params/fuel.json
app.use("/params", express.static("params", {}))


var server = app.listen(8081, function () {

  var host = server.address().address
  var port = server.address().port

  log.info("Example app listening at http://%s:%s", host, port)

});

