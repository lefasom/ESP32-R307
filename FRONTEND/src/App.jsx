import React, { useState, useEffect, useRef } from 'react';

// URL del WebSocket, asegúrate de que esta sea la IP real de tu ESP32
const WEBSOCKET_URL = 'ws://192.168.100.15:80'; 
const RECONNECT_TIMEOUT = 3000; // Intenta reconectar cada 3 segundos
const PING_INTERVAL = 30000; // Envía ping cada 30 segundos
const PONG_TIMEOUT = 5000; // Espera pong por 5 segundos

function WebSocketClient() {
    const [messages, setMessages] = useState([]);
    const [socket, setSocket] = useState(null);
    const [status, setStatus] = useState('Desconectado');
    
    // Referencias para manejar timers
    const pingIntervalRef = useRef(null);
    const pongTimeoutRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);
    const isReconnectingRef = useRef(false);

    // Función para limpiar todos los timers
    const clearAllTimers = () => {
        if (pingIntervalRef.current) {
            clearInterval(pingIntervalRef.current);
            pingIntervalRef.current = null;
        }
        if (pongTimeoutRef.current) {
            clearTimeout(pongTimeoutRef.current);
            pongTimeoutRef.current = null;
        }
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }
    };

    // Función para enviar ping
    const sendPing = (ws) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            console.log('📡 Enviando ping...');
            ws.send(JSON.stringify({ type: 'ping' }));
            
            // Configura timeout para esperar pong
            pongTimeoutRef.current = setTimeout(() => {
                console.log('⚠️ No se recibió pong, cerrando conexión...');
                ws.close();
            }, PONG_TIMEOUT);
        }
    };

    // Función para manejar pong recibido
    const handlePong = () => {
        console.log('🏓 Pong recibido');
        if (pongTimeoutRef.current) {
            clearTimeout(pongTimeoutRef.current);
            pongTimeoutRef.current = null;
        }
    };

    // Función para inicializar el sistema de ping-pong
    const startPingPong = (ws) => {
        // Limpia cualquier interval previo
        if (pingIntervalRef.current) {
            clearInterval(pingIntervalRef.current);
        }

        // Configura el intervalo de ping
        pingIntervalRef.current = setInterval(() => {
            sendPing(ws);
        }, PING_INTERVAL);

        console.log(`🔄 Sistema ping-pong iniciado (cada ${PING_INTERVAL/1000}s)`);
    };

    useEffect(() => {
        const connect = () => {
            // Evita múltiples intentos de reconexión simultáneos
            if (isReconnectingRef.current) return;
            
            console.log('🌐 Intentando conectar al servidor WebSocket...');
            setStatus('Conectando...');
            isReconnectingRef.current = true;
            
            const ws = new WebSocket(WEBSOCKET_URL);

            ws.onopen = () => {
                console.log('✅ Conectado al servidor WebSocket');
                setStatus('Conectado');
                setSocket(ws);
                isReconnectingRef.current = false;
                
                // Inicia el sistema de ping-pong
                startPingPong(ws);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    
                    if (data.type === 'pong') {
                        // Maneja pong sin mostrarlo como mensaje
                        handlePong();
                        return;
                    }
                    
                    // Maneja otros tipos de mensajes
                    console.log('💌 Mensaje recibido:', event.data);
                    setMessages(prevMessages => [...prevMessages, event.data]);
                    
                } catch {
                    // Si no es JSON, trata como mensaje normal
                    console.log('💌 Mensaje recibido:', event.data);
                    setMessages(prevMessages => [...prevMessages, event.data]);
                }
            };

            ws.onclose = (event) => {
                console.log('❌ Desconectado del servidor WebSocket');
                setStatus('Desconectado');
                setSocket(null);
                
                // Limpia timers
                clearAllTimers();
                
                // Solo intenta reconectar si no fue un cierre manual
                if (event.code !== 1000) {
                    isReconnectingRef.current = false;
                    console.log(`🔄 Reintentando conexión en ${RECONNECT_TIMEOUT/1000}s...`);
                    reconnectTimeoutRef.current = setTimeout(connect, RECONNECT_TIMEOUT);
                } else {
                    isReconnectingRef.current = false;
                }
            };

            ws.onerror = (error) => {
                console.error('⚠️ Error de WebSocket:', error);
                setStatus('Error');
                isReconnectingRef.current = false;
            };
        };

        connect(); // Inicia la conexión
        
        // Limpia al desmontar el componente
        return () => {
            clearAllTimers();
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.close(1000, 'Componente desmontado'); // Cierre manual
            }
        };
    }, []); // El array de dependencias vacío asegura que se ejecute solo una vez

    const sendMessage = () => {
        if (socket && socket.readyState === WebSocket.OPEN) {
            const message = '¡ Hola desde React te envio un mensaje !';
            socket.send(JSON.stringify({ type: 'message', content: message }));
            console.log('🚀 Mensaje enviado:', message);
        } else {
            console.log('⚠️ Conexión WebSocket no lista.');
        }
    };

    return (
        <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
            <h1>WebSocket con ESP32 y React (con Ping-Pong)</h1>
            <p>Estado: <strong>{status}</strong></p>
            <p>Asegúrate de que tu computadora y el ESP32 estén en la misma red Wi-Fi.</p>
            <button 
                onClick={sendMessage} 
                disabled={status !== 'Conectado'}
                style={{
                    padding: '10px 20px', 
                    fontSize: '16px', 
                    cursor: status === 'Conectado' ? 'pointer' : 'not-allowed'
                }}
            >
                Enviar mensaje
            </button>
            <hr />
            <h2>Mensajes Recibidos:</h2>
            <ul style={{ listStyleType: 'none', padding: 0 }}>
                {messages.map((msg, index) => (
                    <li key={index} style={{
                        padding: '8px', 
                        borderBottom: '1px solid #eee'
                    }}>
                        {msg}
                    </li>
                ))}
            </ul>
        </div>
    );
}

export default WebSocketClient;