const { app } = window.comfyAPI.app;
const { api } = window.comfyAPI.api;

function downloadArchive(node) {
    const current = node._animaQueueArchive;
    if (!current) {
        return;
    }
    const params = new URLSearchParams({
        filename: current.filename ?? "",
        subfolder: current.subfolder ?? "",
        type: current.type ?? "output",
    });
    const link = document.createElement("a");
    link.href = api.apiURL(`/view?${params.toString()}`);
    link.download = current.filename ?? "anima_queue.zip";
    document.body.appendChild(link);
    link.click();
    link.remove();
}

app.registerExtension({
    name: "AnimaVariationBatch.DownloadQueueZip",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "AnimaSaveQueueZip") {
            return;
        }

        const originalOnExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (output) {
            originalOnExecuted?.apply(this, arguments);

            const archive = output?.zip?.[0];
            if (!archive) {
                return;
            }
            this._animaQueueArchive = archive;

            let widget = this.widgets?.find(
                (item) => item.name === "_download_zip"
            );
            if (!widget) {
                widget = this.addWidget(
                    "button",
                    "_download_zip",
                    "Download ZIP",
                    () => downloadArchive(this)
                );
            }
            widget.value = `Download ZIP (${archive.count ?? 0} images)`;
            this.setDirtyCanvas(true, true);

            const archiveKey = `${archive.subfolder}/${archive.filename}`;
            if (
                archive.auto_download &&
                this._animaLastAutoDownload !== archiveKey
            ) {
                this._animaLastAutoDownload = archiveKey;
                downloadArchive(this);
            }
        };
    },
});
