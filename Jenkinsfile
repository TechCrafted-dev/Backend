pipeline {
    agent any

    /*────────────────────────────
      Variables de entorno
    ────────────────────────────*/
    environment {
        // --- Docker ---
        REPO_NAME   = 'techcrafted-api'
        TAG         = "${REPO_NAME}:${env.BRANCH_NAME}"
        PROD_NAME   = 'techcrafted-api'  // Contenedor producción
        PROD_PORT   = '3000'             // Puerto producción
        FOLDER   = "/mnt/Data/Contenedores/Backend_TechCrafted.dev/"

        // --- Telegram (credenciales en Jenkins) ---
        TG_TOKEN    = credentials('TELEGRAM_TOKEN')
        TG_CHAT     = credentials('TELEGRAM_CHAT_ID')
    }

    stages {

        /* Notificación de arranque */
        stage('Notify start') {
            steps {
                sh """
                    curl -s -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
                         -d chat_id=${TG_CHAT} \
                         -d text="🚀 *${env.BRANCH_NAME}*: build iniciado (commit ${GIT_COMMIT})" \
                         -d parse_mode=Markdown
                """
            }
        }

        /* Compilar imagen Docker */
        stage('Build image') {
            steps {
                sh """
                    docker build --pull \
                                 --build-arg VCS_REF=${GIT_COMMIT} \
                                 -t ${TAG} .
                """
            }
        }

        /* Desplegar en producción (solo main) */
        stage('Deploy to PROD') {
            when { expression { env.BRANCH_NAME == 'main' } }
            steps {
                sh """
                    docker stop ${PROD_NAME} || true
                    docker rm   ${PROD_NAME} || true
                    docker run -d --name ${PROD_NAME} \
                                 --restart unless-stopped \
                                 -v ${FOLDER}:/app/data \
                                 -p ${PROD_PORT}:3000 \
                                 ${TAG}
                """
            }
        }

        /* sandbox para ramas que no sean main */
        /*
        stage('Deploy to Sandbox') {
            when { expression { env.BRANCH_NAME != 'main' } }
            steps {
                script {
                    // El nombre y puerto del sandbox dependen de la rama
                    def SB_NAME = "blog-${env.BRANCH_NAME}"
                    def SB_PORT = env.BRANCH_NAME == 'dev' ? '8080' : '8081'
                    sh """
                        docker stop ${SB_NAME} || true
                        docker rm   ${SB_NAME} || true
                        docker run -d --name ${SB_NAME} \
                                     --restart unless-stopped \
                                     -p ${SB_PORT}:3000 ${TAG}
                    """
                }
            }
        }
        */

    }

    /*────────────────────────────
      Bloque post para notificar
    ────────────────────────────*/
    post {
        success {
            sh """
                curl -s -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
                     -d chat_id=${TG_CHAT} \
                     -d text="✅ *${env.BRANCH_NAME}* desplegado con éxito${env.BRANCH_NAME == 'main' ? ' en producción' : ''}" \
                     -d parse_mode=Markdown
            """
        }
        failure {
            sh """
                curl -s -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
                     -d chat_id=${TG_CHAT} \
                     -d text="❌ Falló el build de *${env.BRANCH_NAME}*. Revisa Jenkins." \
                     -d parse_mode=Markdown
            """
        }
    }
}
