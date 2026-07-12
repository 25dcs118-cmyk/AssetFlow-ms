FROM odoo:17

USER root
COPY assetflow /mnt/extra-addons/assetflow
COPY entrypoint.sh /entrypoint.sh
RUN chown -R odoo:odoo /mnt/extra-addons/assetflow && chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
