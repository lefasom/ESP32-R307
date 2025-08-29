import React, { useState } from 'react';
import { initializeApp } from 'firebase/app';
import { getDatabase, ref, set, onValue } from 'firebase/database';

// 1. Configuración de Firebase
// Con los valores proporcionados por el usuario
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

// 2. Inicializa Firebase de forma modular
const app = initializeApp(firebaseConfig);
const database = getDatabase(app);

const App = () => {
  const [status, setStatus] = useState('Listo para recibir comandos.');
  const [loading, setLoading] = useState(false);

  // 3. Lógica para enviar comandos y escuchar respuestas
  const sendCommand = async (commandType) => {
    setLoading(true);
    setStatus(`Enviando comando: ${commandType}...`);
    const timestamp = Date.now();
    const commandData = {
      command: commandType,
      timestamp: timestamp,
      status: 'pending'
    };

    try {
      const dbRef = ref(database, 'commands/esp32_command');
      await set(dbRef, commandData);
      setStatus(`Comando "${commandType}" enviado. Esperando respuesta...`);
      listenForResponse(timestamp);
    } catch (error) {
      console.error("Error al enviar el comando: ", error);
      setStatus('❌ Error al enviar el comando.');
      setLoading(false);
    }
  };

  const listenForResponse = (timestamp) => {
    const dbRef = ref(database, 'commands/esp32_command');
    onValue(dbRef, (snapshot) => {
      const data = snapshot.val();
      if (data && data.timestamp === timestamp) {
        if (data.status === 'completed') {
          setStatus(`✅ Comando "${data.command}" completado.`);
          setLoading(false);
        } else if (data.status === 'error') {
          setStatus(`❌ Error al ejecutar el comando "${data.command}".`);
          setLoading(false);
        } else {
          setStatus(`Comando "${data.command}" en progreso...`);
        }
      }
    });
  };

  // 4. Estructura de la interfaz de usuario con solo los botones
  return (
    <div style={{ fontFamily: 'Arial, sans-serif', padding: '20px', maxWidth: '600px', margin: 'auto', textAlign: 'center' }}>
      <h1>Sistema de Acceso con Huella</h1>
      <p>Presiona el botón para enviar un comando al sensor R307 a través de Firebase.</p>
      
      <div style={{ margin: '20px 0' }}>
        <button
          onClick={() => sendCommand('agregar_huella')}
          disabled={loading}
          style={{ marginRight: '10px', padding: '12px 24px', fontSize: '16px', cursor: loading ? 'not-allowed' : 'pointer' }}
        >
          Agregar Huella
        </button>
        <button
          onClick={() => sendCommand('detectar_huella')}
          disabled={loading}
          style={{ padding: '12px 24px', fontSize: '16px', cursor: loading ? 'not-allowed' : 'pointer' }}
        >
          Detectar Huella
        </button>
      </div>

      <p style={{ fontWeight: 'bold', minHeight: '20px' }}>{status}</p>
    </div>
  );
};

export default App;