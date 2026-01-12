// static/js/simulator.js
class MROSimulator {
    constructor() {
        this.currentScenario = null;
        this.timer = null;
        this.timeLeft = 0;
        this.userScore = 0;
        this.userLevel = 'Aprendiz';
        
        this.init();
    }
    
    async init() {
        await this.loadUserProgress();
        await this.loadNewScenario();
        this.setupEventListeners();
    }
    
    async loadUserProgress() {
        try {
            // Asume que tienes un endpoint para obtener el progreso del usuario
            const response = await fetch('/api/simulator/progress');
            const data = await response.json();
            
            this.userScore = data.score || 0;
            this.userLevel = data.level || 'Aprendiz';
            
            // Actualizar la UI
            document.getElementById('user-score').textContent = this.userScore;
            document.getElementById('user-level').textContent = this.userLevel;
            document.getElementById('completed-scenarios').textContent = data.completed || 0;
            document.getElementById('effectiveness-rate').textContent = data.effectiveness || '0%';
            
            // Calcular progreso del nivel (ejemplo)
            const levelProgress = (this.userScore % 500) / 5; // 500 puntos por nivel
            document.getElementById('level-progress').style.width = `${levelProgress}%`;
            
        } catch (error) {
            console.error('Error cargando progreso:', error);
        }
    }
    
    async loadNewScenario() {
        try {
            const response = await fetch('/api/simulator/scenario');
            this.currentScenario = await response.json();
            
            this.renderScenario();
            this.startTimer();
            
        } catch (error) {
            console.error('Error cargando escenario:', error);
            alert('No se pudo cargar un nuevo escenario. Recarga la página.');
        }
    }
    
    renderScenario() {
        const s = this.currentScenario;
        
        document.getElementById('scenario-title').textContent = s.title;
        document.getElementById('scenario-category').textContent = `[${s.category}]`;
        document.getElementById('scenario-description').textContent = s.description;
        document.getElementById('sap-data').textContent = s.sap_data;
        document.getElementById('affected-line').textContent = s.affected_line;
        document.getElementById('time-limit').textContent = s.time_limit;
        
        this.timeLeft = s.time_limit;
        this.updateTimerDisplay();
        
        // Renderizar opciones
        const optionsContainer = document.getElementById('decision-options');
        optionsContainer.innerHTML = '';
        
        for (const [key, text] of Object.entries(s.options)) {
            const optionDiv = document.createElement('div');
            optionDiv.className = 'option-card mb-2';
            optionDiv.innerHTML = `
                <button class="btn btn-outline-primary w-100 text-start option-btn" data-option="${key}">
                    <span class="option-letter badge bg-primary me-2">${key}</span>
                    ${text}
                </button>
            `;
            optionsContainer.appendChild(optionDiv);
        }
        
        // Ocultar panel de feedback
        document.getElementById('feedback-panel').classList.add('d-none');
    }
    
    startTimer() {
        if (this.timer) clearInterval(this.timer);
        
        this.timer = setInterval(() => {
            this.timeLeft--;
            this.updateTimerDisplay();
            
            if (this.timeLeft <= 0) {
                clearInterval(this.timer);
                this.handleTimeUp();
            }
        }, 1000);
    }
    
    updateTimerDisplay() {
        const timerElement = document.getElementById('time-limit');
        if (timerElement) {
            timerElement.textContent = this.timeLeft;
            
            // Cambiar color según el tiempo restante
            if (this.timeLeft < 10) {
                timerElement.className = 'text-danger fw-bold';
            } else if (this.timeLeft < 30) {
                timerElement.className = 'text-warning';
            } else {
                timerElement.className = 'text-success';
            }
        }
    }
    
    handleTimeUp() {
        alert('¡Tiempo agotado! Se considerará como respuesta incorrecta.');
        // Aquí podrías enviar automáticamente una respuesta o manejarlo como error
    }
    
    async submitDecision(selectedOption) {
        clearInterval(this.timer); // Detener el temporizador
        
        try {
            const response = await fetch('/api/simulator/evaluate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    scenario_id: this.currentScenario.id,
                    selected_option: selectedOption,
                    time_taken: this.currentScenario.time_limit - this.timeLeft
                })
            });
            
            const feedback = await response.json();
            this.showFeedback(feedback);
            await this.loadUserProgress(); // Actualizar puntuación
            
        } catch (error) {
            console.error('Error evaluando decisión:', error);
        }
    }
    
    showFeedback(feedback) {
        const feedbackPanel = document.getElementById('feedback-panel');
        const header = document.getElementById('feedback-header');
        const body = document.getElementById('feedback-body');
        
        // Configurar encabezado según si fue correcto o no
        if (feedback.is_correct) {
            header.className = 'card-header bg-success text-white';
            header.innerHTML = `<h5 class="mb-0"><i class="fas fa-check-circle"></i> Decisión Correcta! +${feedback.points_earned} puntos</h5>`;
        } else {
            header.className = 'card-header bg-danger text-white';
            header.innerHTML = `<h5 class="mb-0"><i class="fas fa-times-circle"></i> Decisión Incorrecta. Respuesta correcta: ${feedback.correct_option}</h5>`;
        }
        
        // Llenar el cuerpo con el feedback
        body.innerHTML = `
            <div class="alert ${feedback.is_correct ? 'alert-success' : 'alert-danger'}">
                ${feedback.feedback_text}
            </div>
            
            <h6>Análisis Profesional:</h6>
            <p>${feedback.professional_analysis}</p>
            
            <h6>Procedimiento SAP Correcto:</h6>
            <ol>
                ${feedback.sap_procedure.map(step => `<li>${step}</li>`).join('')}
            </ol>
            
            <div class="alert alert-info">
                <strong>Aprendizaje clave:</strong> ${feedback.key_learning}
            </div>
        `;
        
        // Mostrar el panel
        feedbackPanel.classList.remove('d-none');
        
        // Desplazar la vista hacia el feedback
        feedbackPanel.scrollIntoView({ behavior: 'smooth' });
    }
    
    setupEventListeners() {
        // Delegar evento a los botones de opción
        document.getElementById('decision-options').addEventListener('click', (e) => {
            if (e.target.closest('.option-btn')) {
                const selectedOption = e.target.closest('.option-btn').dataset.option;
                this.submitDecision(selectedOption);
            }
        });
        
        // Botón siguiente escenario
        document.getElementById('btn-next-scenario').addEventListener('click', () => {
            this.loadNewScenario();
        });
        
        // Botón llamar al supervisor (simulado)
        document.getElementById('btn-call-supervisor').addEventListener('click', () => {
            alert('[SIMULACIÓN] Supervisor: "Revise el procedimiento en el manual MRO-045 antes de proceder."');
            // Podría descontar puntos por pedir ayuda innecesaria
        });
    }
}

// Inicializar el simulador cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.simulator = new MROSimulator();
});
