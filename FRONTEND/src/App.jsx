import React, { useState, useEffect } from 'react';
import { initializeApp } from 'firebase/app';
import { getDatabase, ref, set, onValue, off } from 'firebase/database';

// Configuración de Firebase
const firebaseConfig = {
    apiKey: "AIzaSyCRO9H94xbbFul4NmOSAawG7rF784I7-6U",
    authDomain: "esp32-a8053.firebaseapp.com",
    databaseURL: "https://esp32-a8053-default-rtdb.firebaseio.com",
    projectId: "esp32-a8053",
    storageBucket: "esp32-a8053.firebasestorage.app",
    messagingSenderId: "953937716607",
    appId: "1:953937716607:web:4fae054f8c769f88b1e64a",
    measurementId: "G-NHW47VF23M"
};

// Inicializar Firebase una sola vez
const app = initializeApp(firebaseConfig);
const database = getDatabase(app);

const App = () => {
    const [display, setDisplay] = useState('');
    const [display2, setDisplay2] = useState('');
    const [loading, setLoading] = useState(false);

    const displayStyle = {
        backgroundColor: 'black',
        color: 'rgb(0, 255, 0)',
        fontSize: '1rem',
        fontFamily: 'monospace',
        padding: '20px',
        textAlign: 'center',
        borderRadius: '10px',
        width: '60%',
        display: 'flex',
        flexDirection:'column',
        margin: '10px auto',
        height: '80px',
        alignItems: 'start',
    };
     const box = {
        color: 'hsla(188, 100%, 59%, 0.95)',
        fontSize: '1rem',
      
    };
    const box2 = {
        color: 'rgba(140, 255, 0, 1)',
        fontSize: '2rem',
        margin: '10px 0',
      
    };
    // Un solo useEffect para gestionar ambos listeners
    useEffect(() => {
        const displayRef = ref(database, 'display');
        const displayRef2 = ref(database, 'display2');

        const unsubscribeDisplay = onValue(displayRef, (snapshot) => {
            const data = snapshot.val();
            if (data && data.mensaje) {
                setDisplay(data.mensaje);
            }
        }, (error) => {
            console.error("Error al escuchar cambios en display:", error);
            setLoading(false);
        });

        const unsubscribeDisplay2 = onValue(displayRef2, (snapshot) => {
            const data = snapshot.val();
            if (data) {
                setDisplay2(data.result);
            }
        }, (error) => {
            console.error("Error al escuchar cambios en display2:", error);
            setLoading(false);
        });

        // Cleanup function para remover los listeners cuando el componente se desmonte
        return () => {
            off(displayRef, 'value', unsubscribeDisplay);
            off(displayRef2, 'value', unsubscribeDisplay2);
        };
    }); // El array vacío asegura que el efecto se ejecute solo una vez

    // ... El resto del código del componente App es igual
    const sendCommand = async (commandType) => {
        if (loading) return; 

        setLoading(true);
        const timestamp = Date.now();
        const commandData = {
            command: commandType,
            timestamp: timestamp,
            status: 'pending'
        };

        try {
            const commandRef = ref(database, 'commands/esp32_command');
            await set(commandRef, commandData);
            
            setTimeout(() => {
                    setLoading(false);
            }, 10000); 
            
        } catch (error) {
            console.error("Error al enviar el comando:", error);
            setLoading(false);
        }
    };

    return (
        <div style={{ 
            fontFamily: 'Arial, sans-serif', 
            padding: '20px', 
            maxWidth: '600px', 
            margin: 'auto', 
            textAlign: 'center',
            backgroundColor: '#f5f5f5',
            minHeight: '100vh'
        }}>
            <h1 style={{ color: '#333', marginBottom: '10px' }}>Sistema de Acceso con Huella</h1>
            <p style={{ color: '#666', marginBottom: '30px' }}>
                Presiona el botón para enviar un comando al sensor R307 a través de Firebase.
            </p>

            <div style={displayStyle}>
              <span style={box}>{display || 'Esperando datos del ESP32...'}</span>
              <span style={box2}> {display2 || ''}</span>
            </div>
            <div style={{ margin: '30px 0' }}>
                <button
                    onClick={() => sendCommand('agregar_huella')}
                    disabled={loading}
                    style={{
                        marginRight: '15px',
                        marginBottom: '10px',
                        padding: '12px 24px',
                        fontSize: '16px',
                        cursor: loading ? 'not-allowed' : 'pointer',
                        backgroundColor: loading ? '#ccc' : '#4CAF50',
                        color: 'white',
                        border: 'none',
                        borderRadius: '5px',
                        transition: 'background-color 0.3s'
                    }}
                >
                    {loading ? '⏳ Procesando...' : '➕ Agregar Huella'}
                </button>
                
                <button
                    onClick={() => sendCommand('detectar_huella')}
                    disabled={loading}
                    style={{
                        marginBottom: '10px',
                        padding: '12px 24px',
                        fontSize: '16px',
                        cursor: loading ? 'not-allowed' : 'pointer',
                        backgroundColor: loading ? '#ccc' : '#2196F3',
                        color: 'white',
                        border: 'none',
                        borderRadius: '5px',
                        transition: 'background-color 0.3s'
                    }}
                >
                    {loading ? '⏳ Procesando...' : '🔍 Detectar Huella'}
                </button>
            </div>

        </div>
    );
};

export default App;