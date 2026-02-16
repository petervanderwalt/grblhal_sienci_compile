import { WebSerial } from './webserial.js';

export class SerialTerminal {
    constructor(containerId) {
        this.ws = new WebSerial();
        this.container = document.getElementById(containerId);

        // Initialize Xterm
        this.term = new Terminal({
            cursorBlink: true,
            fontSize: 14,
            theme: {
                background: '#1a1a1a',
                foreground: '#f0f0f0'
            }
        });

        this.fitAddon = new FitAddon.FitAddon();
        this.term.loadAddon(this.fitAddon);
        this.term.open(this.container);
        this.fitAddon.fit();

        // Handle Terminal Input (Typing)
        this.term.onData(data => {
            if (this.ws.isConnected) {
                this.ws.write(data);
            }
        });

        // Handle Incoming Serial Data
        this.ws.on('line', (line) => {
            this.term.writeln(line);
        });

        this.ws.on('error', (err) => {
            this.term.writeln(`\x1b[31m[ERROR] ${err.message}\x1b[0m`);
        });

        this.ws.on('connect', () => {
            this.term.writeln('\x1b[32m[CONNECTED]\x1b[0m');
            document.getElementById('terminal-connect').textContent = 'Disconnect';
        });

        this.ws.on('disconnect', () => {
            this.term.writeln('\x1b[31m[DISCONNECTED]\x1b[0m');
            document.getElementById('terminal-connect').textContent = 'Connect Serial';
        });
    }

    async toggleConnect() {
        if (this.ws.isConnected) {
            await this.ws.disconnect();
        } else {
            try {
                await this.ws.connect(115200);
            } catch (e) {
                console.error(e);
            }
        }
    }

    sendLine(cmd) {
        if (this.ws.isConnected) {
            this.ws.sendCommand(cmd);
        }
    }
}
