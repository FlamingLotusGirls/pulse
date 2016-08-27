// This is a quick-and-dirty server for testing the REST and UDP connectors
// for the Android UI.

const express = require('express');
const app = express();
const child_process = require('child_process');
const toString = require('stream-to-string');
const log = require('./log.js');
const dgram = require('dgram');
const util = require('util');
const os = require('os');

Array.prototype.contains = function contains(val) {
    for (var v of this) {
        if (v === val) {
            return true;
        }
    }
    return false;
}

var ENABLE_HEARTBEAT = process.argv.contains('--heartbeat')

var HEARTBEAT_PORT = 5000;
var CMD_PORT = 5001;
// UDP Packet is in big-endian order.
//const BIGENDIAN = endian();
const BIGENDIAN = false;

app.get('/', (req, res) => res.send("Hello, World"));

function runCmd(cmd, ...args) {
    return new Promise((accept, reject) => {
        newline();
	    log.info("Running %s, %j", cmd, args)
	    let proc = child_process.execFile(cmd, args);
	    proc.stdout.on('error', e => {
            newline();
	        log.error("IO Error: , %s", e.stack);
	        reject(e);
	    });
	    let out = toString(proc.stdout);
	    proc
	        .on('error', reject)
	        .on('exit', (code, signal) => {
		        if (code === 0) {
                    newline();
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
    });
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
    source_1: 1,
    bpm_1: 60,
    source_2: 1,
    bpm_2: 60,
    source_3: 1,
    bpm_3: 60,
    bpm: 60
};

// Do a PUT request to:
// http://localhost:8081/val?param=slider1&value=5
// We use PUT to set, GET to get
app.put('/val', (req, res) => {
    // Get the supplied query parameters
    let param = req.query.param
    let value = Number(req.query.value);
    newline();
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
    newline();
    log.info("Set %s to %d", param, value);
    res.send({status: "OK", param: param, value: value});
});

app.put('/trigger', (req, res) => {
    let event = req.query.name;
    newline();
    log.info("Trigger %s", event);
    // A delay before sending confirmation to allow the UI feedback to be visible.
    setTimeout(() => res.send({status: "OK", name: event}), 1500);
});

app.get('/status', (req, res) => {
    res.send({status: "OK", params: PARAMS, nodes: {node1: "OK", node2: "OK"}});
});

// Send files in the params/ subdirectory. Use ".json" for json files, .txt for text files.
// http://localhost:8081/params/fuel.json
app.use("/params", express.static("params", {}))

var server = app.listen(8081, () => {
    var host = server.address().address
    var port = server.address().port

    log.info("Test app listening at http://%s:%d", host, port);
});

// UDP handling code.

const RE_IP = /^(25[0-5]|2[0-4]\d|[01]?\d\d|\d)\.(25[0-5]|2[0-4]\d|[01]?\d\d|\d)\.(25[0-5]|2[0-4]\d|[01]?\d\d|\d)\.(25[0-5]|2[0-4]\d|[01]?\d\d|\d)$/;

// Parse an IP address
function parseIP4(addr) {
    let parse = addr.match(RE_IP);
    if (parse) {
        let [ip, b0, b1, b2, b3] = parse;
        return [b0, b1, b2, b3].map((n) => parseInt(n));
    }
}

function makeBroadcast(ip, netmask) {
    ip = parseIP4(ip);
    netmask = parseIP4(netmask);
    let reverse =  [
        255 ^ netmask[0],
        255 ^ netmask[1],
        255 ^ netmask[2],
        255 ^ netmask[3]
    ];
    return ip.map((b, i) => (b & netmask[i]) | reverse[i]);
}

function unparseIP4(addr) {
    return addr.join(".");
}

// Get all the broadcast addresses to send to, plus localhost
function getBroadcastAddresses() {
    const result = [];
    const interfaces = os.networkInterfaces();
    for (let ifaceName in interfaces) {
        let ifaces = interfaces[ifaceName];
        ifaces.forEach(iface => {
            if (!iface.internal && (iface.family == 'IPv4')) {
                let broadcast = makeBroadcast(iface.address, iface.netmask);
                // exclude link-local (unconfigured)
                if ((broadcast[0] != 169) || (broadcast[1] != 254)) {
                    result.push(unparseIP4(broadcast));
                }
            }
        });
    }
    result.push('127.0.0.1');
    return result;
}

const udp_pulse = dgram.createSocket({type: 'udp4', reuseAddr: true})
      .on('listening', () => udp_pulse.setBroadcast(true));

try {
    udp_pulse
      .bind({port: HEARTBEAT_PORT})
} catch (e) {
    console.log.error
}

var seq = 0;
var hpos = 0;
function newline() {
    if (hpos > 0) {
        process.stdout.write("\n");
        hpos = 0;
    }
}
const BROADCAST = getBroadcastAddresses();
BROADCAST.forEach(addr => log.info("Broadcasting heartbeat to %s:%d", addr, HEARTBEAT_PORT));

function sendPulse(id) {
    if (!ENABLE_HEARTBEAT) return;
    try {
        const c = '-+==!#$@%^&.,/?'[id];
        process.stdout.write(c);
        hpos++;
        const message = Buffer.alloc(16);
        message.fill(0);
        message.writeUInt8(id, 0); // pod_id
        seq = (seq + 1) && 0xff;
        message.writeUInt8(seq, 1);    // rolling_sequence
        writeUInt16(message, 1000, 2); // beat_interval_ms
        writeUInt32(message, 1000, 4);    // elapsed_ms
        writeFloat(message, 60.0, 8);  // est_BPM
        writeUInt32(message, Date.now() & 0xfffffff, 12); // time
        // Send to network and localhost port 5000;
        // Must set up emulator to forward:
        //   telnet to emulator, authorize, and enter
        //   redir add udp:5000:5000
        BROADCAST.forEach((addr) => udp_pulse.send(message, HEARTBEAT_PORT, addr));
    } catch (e) {
        newline();
        error.log("Error: " + e);
    }
}
function autobeat() {
    sendPulse(0);
    setTimeout(autobeat, (60*1000)/PARAMS.bpm);
}
autobeat();
setInterval(() => sendPulse(1), 844);
setInterval(() => sendPulse(2), 1000);
setInterval(() => sendPulse(3), 823);
setInterval(() => sendPulse(4), 1200);

function readUInt16(msg, idx) {
    if (BIGENDIAN) {
        return msg.readUInt16BE(idx);
    } else {
        return msg.readUInt16LE(idx);
    }
}

function writeUInt16(msg, data, idx) {
    if (BIGENDIAN) {
        return msg.writeInt16BE(data, idx);
    } else {
        return msg.writeUInt16LE(data, idx);
    }
}

function readUInt32(msg, idx) {
    if (BIGENDIAN) {
        return msg.readUInt32BE(idx);
    } else {
        return msg.readUInt32LE(idx);
    }
}

function writeUInt32(msg, data, idx) {
    if (BIGENDIAN) {
        return msg.writeUInt32BE(data, idx);
    } else {
        return msg.writeUInt32LE(data, idx);
    }
}

function readFloat(msg, idx) {
    if (BIGENDIAN) {
        return msg.readFloatBE(idx);
    } else {
        return msg.readFloatLE(idx);
    }
}

function writeFloat(msg, data, idx) {
    if (BIGENDIAN) {
        return msg.writeFloatBE(data, idx);
    } else {
        return msg.writeFloatLE(data, idx);
    }
}

function decode_cmd(msg) {
    if (msg.length < 8) {
        return msg;
    }
    return util.inspect({
        rcv: msg.readUInt8(0),
        trk: msg.readUInt8(1),
        cmd: readUInt16(msg, 2),
        data: readUInt32(msg, 4)
    });
}

const udp_cmd = dgram.createSocket({type: 'udp4', reuseAddr: true});

function show(msg, info) {
    try {
        newline();
        log.info(`UDP port ${info.address}:${CMD_PORT} => ${decode_cmd(msg)} (${info.size} bytes)`);
    } catch (e) {
        newline();
        log.error("Log failure: %s", e.message);
    }
}

function setBPM(msg, info) {
    let rcv = msg.readUInt8(0);
    let cmd = readUInt16(msg, 2);
    let data = readUInt32(msg, 4);
    if ((rcv === 0) && (cmd === 2)) {
        PARAMS.bpm = data;
    }
}

udp_cmd
    .on('error', (err) => log.error("Binding Error", err))
    .on('listening', () => log.info(`Listening on UDP interface ${udp_cmd.address().address} port ${udp_cmd.address().port}`))
    .on('message', setBPM)
    .on('message', show)
    .bind({port: CMD_PORT});

function decode_heartbeat(msg) {
    try {
        if (msg.length < 16) {
            return "Length = " + msg.length;
        }
        return util.inspect({
            pod: msg.readUInt8(0),
            seq: msg.readUInt8(1),
            interval: readUInt16(msg, 2),
            elapsed: readUInt32(msg, 4),
            est_BPM: readFloat(msg, 8),
            time: readUInt32(msg, 12)
        });
    } catch (e) {
        return {
            err: e.message
        }
    }
}

/*
udp_pulse
    .on('message', (msg, info) => console.log("PULSE", decode_heartbeat(msg)));
*/
