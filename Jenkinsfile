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

        // --- Telegram ---
        TG_TOKEN    = credentials('TELEGRAM_TOKEN')
        TG_CHAT     = credentials('TELEGRAM_CHAT_ID')
    }

    /*────────────────────────────
        Etapas del pipeline
    ────────────────────────────*/

    stages {
        /* Notificación de inicio */
        stage('Notify start') {
            steps {
                script {
                    // Hash corto (8 caracteres) — evita mensajes demasiado largos
                    def shortCommit = env.GIT_COMMIT.take(8)

                    // Mensaje HTML multilínea
                    def msg = """
                        <b>📦 ${env.REPO_NAME}</b>
                        <b>Branch:</b> ${env.BRANCH_NAME}
                        <b>Commit:</b> <code>${shortCommit}</code>

                        🏗️ Build iniciado…
                    """.stripIndent().trim()

                    // Llamada al bot
                    sh """
                        curl -s -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
                             --data-urlencode "chat_id=${TG_CHAT}" \
                             --data-urlencode "text=${msg}" \
                             -d parse_mode=HTML
                    """
                }
            }
        }

        /* Desplegar en producción*/
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
    }

    /*────────────────────────────
      Bloque post para notificar
    ────────────────────────────*/
    post {
        success {
            script {
                def msg = """
                    <b>✅ Despliegue completado</b>
                    Todo salió bien.
                """.stripIndent().trim()

                sh """
                    curl -s "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \\
                         --data-urlencode "chat_id=${TG_CHAT}" \\
                         --data-urlencode "text=${msg}" \\
                         -d parse_mode=HTML
                """
            }
        }

        failure {
            script {
                def msg = """
                    <b>❌ Build fallido</b>
                    Revisa Jenkins para más detalles.
                """.stripIndent().trim()

                sh """
                    curl -s "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \\
                         --data-urlencode "chat_id=${TG_CHAT}" \\
                         --data-urlencode "text=${msg}" \\
                         -d parse_mode=HTML
                """
            }
        }
    }
}