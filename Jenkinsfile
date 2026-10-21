// Pipeline para agente Jenkins em Windows (usa `bat`).
// Requer Python 3 disponível no PATH do agente.
pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    stages {
        stage('Preparar ambiente') {
            steps {
                bat 'python -m venv .venv'
                bat '.venv\\Scripts\\python -m pip install --upgrade pip'
                bat '.venv\\Scripts\\python -m pip install -r requirements-dev.txt'
            }
        }

        stage('Lint') {
            steps {
                // Falha em erros de sintaxe/nomes indefinidos; o restante é apenas aviso.
                bat '.venv\\Scripts\\python -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude=.venv'
                bat '.venv\\Scripts\\python -m flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics --exclude=.venv'
            }
        }

        stage('Testes') {
            steps {
                bat '.venv\\Scripts\\python -m pytest tests/ -v --tb=short --cov=services --cov-report=xml --cov-report=term --junitxml=pytest-report.xml'
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'pytest-report.xml'
                }
            }
        }

        stage('Segurança') {
            steps {
                catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE') {
                    bat '.venv\\Scripts\\python -m bandit -r services'
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'coverage.xml', allowEmptyArchive: true
        }
    }
}
