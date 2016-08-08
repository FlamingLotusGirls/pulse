var winston = require('winston');
winston.add(winston.transports.File, {
    filename: 'server.log',
    handleExceptions: true,
    humanReadableUnhandledException: true,
    exitOnError: false,
    raw: false,
    json: false,
    logstash: false,
    timestamp: function() {
	return new Date().toISOString()
      },
    formatter: function(options) {
        // Return string will be passed to logger.
        return options.timestamp() +' '+ options.level.toUpperCase() +' '+ (undefined !== options.message ? options.message : '') +
            (options.meta && Object.keys(options.meta).length ? '\n\t'+ JSON.stringify(options.meta) : '' );
    }
});

winston.log('info', 'Initializing...!');

module.exports = winston;
