<script>
	// @ts-nocheck
	import { Camera, CheckCircle, AlertTriangle, XCircle, BarChart2 } from 'lucide-svelte';

	let fileInput = $state();
	let overlayCanvas = $state();
	let imageEl = $state();
	let imagePreview = $state(null);
	let isLoading = $state(false);
	let result = $state(null);
	let errorMsg = $state(null);

	const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

	const handleFileSelect = (event) => {
		const file = event.target.files[0];
		if (!file) return;

		const reader = new FileReader();
		reader.onload = (e) => {
			imagePreview = e.target.result;
		};
		reader.readAsDataURL(file);

		result = null;
		errorMsg = null;
		clearOverlay();
	};

	const clearOverlay = () => {
		if (!overlayCanvas) return;
		const ctx = overlayCanvas.getContext('2d');
		ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
	};

	const drawLandmarks = (landmarks, label) => {
		if (!overlayCanvas || !imageEl) return;

		// Match canvas size to the actual rendered image
		overlayCanvas.width  = imageEl.naturalWidth  || imageEl.clientWidth;
		overlayCanvas.height = imageEl.naturalHeight || imageEl.clientHeight;

		const ctx = overlayCanvas.getContext('2d');
		const w = overlayCanvas.width;
		const h = overlayCanvas.height;
		ctx.clearRect(0, 0, w, h);

		const strokeColor = label === 'correct' ? '#10b981' : '#ef4444';

		const connections = [
			[11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
			[11, 23], [12, 24], [23, 24],
			[23, 25], [25, 27], [24, 26], [26, 28]
		];

		ctx.lineWidth = Math.max(2, w / 200);
		ctx.strokeStyle = strokeColor;
		ctx.lineCap = 'round';

		connections.forEach(([a, b]) => {
			const p1 = landmarks[a];
			const p2 = landmarks[b];
			if (!p1 || !p2) return;
			ctx.beginPath();
			ctx.moveTo(p1.x * w, p1.y * h);
			ctx.lineTo(p2.x * w, p2.y * h);
			ctx.stroke();
		});

		const dotRadius = Math.max(4, w / 140);
		landmarks.forEach(lm => {
			ctx.beginPath();
			ctx.arc(lm.x * w, lm.y * h, dotRadius, 0, 2 * Math.PI);
			ctx.fillStyle = '#ffffff';
			ctx.fill();
			ctx.strokeStyle = strokeColor;
			ctx.lineWidth = 2;
			ctx.stroke();
		});
	};

	const analyzeImage = async () => {
		const file = fileInput?.files[0];
		if (!file) return;

		isLoading = true;
		errorMsg = null;
		result = null;
		clearOverlay();

		const formData = new FormData();
		formData.append('file', file);

		try {
			const res = await fetch(`${API_BASE}/predict/image`, {
				method: 'POST',
				body: formData
			});

			if (!res.ok) {
				const data = await res.json();
				throw new Error(data.detail || 'Failed to analyze image');
			}

			result = await res.json();

			if (result.landmarks) {
				// Allow DOM to settle so imageEl has correct dimensions
				setTimeout(() => drawLandmarks(result.landmarks, result.label), 80);
			}
		} catch (err) {
			errorMsg = err.message;
		} finally {
			isLoading = false;
		}
	};
</script>

<svelte:head>
	<title>Image Analysis | PushupPro</title>
</svelte:head>

<div class="container page-container animate-fade-in">
	<div class="header">
		<h1>Image Analysis</h1>
		<p>Upload a photo of your pushup posture for instant AI evaluation.</p>
	</div>

	<div class="grid layout-grid">
		<!-- Left: Upload & Preview -->
		<div class="upload-section glass-panel">
			<div class="upload-area" class:has-image={imagePreview}>
				{#if imagePreview}
					<div class="image-wrapper">
						<img
							bind:this={imageEl}
							src={imagePreview}
							alt="Preview"
							class="preview-image"
						/>
						<canvas bind:this={overlayCanvas} class="landmark-canvas"></canvas>
					</div>
					<div class="upload-overlay">
						<button class="btn btn-secondary" onclick={() => fileInput.click()}>
							Change Image
						</button>
					</div>
				{:else}
					<div class="empty-state">
						<span class="icon-large"><Camera size={48} /></span>
						<h3>Upload Image</h3>
						<p>JPEG or PNG formats supported</p>
						<button class="btn btn-secondary mt-4" onclick={() => fileInput.click()}>
							Select File
						</button>
					</div>
				{/if}
				<input
					type="file"
					accept="image/jpeg, image/png"
					bind:this={fileInput}
					onchange={handleFileSelect}
					style="display: none;"
				/>
			</div>

			<div class="action-bar">
				<button
					class="btn btn-primary w-full"
					disabled={!imagePreview || isLoading}
					onclick={analyzeImage}
				>
					{#if isLoading}
						<span class="spinner"></span> Analyzing...
					{:else}
						Analyze Posture
					{/if}
				</button>
			</div>
		</div>

		<!-- Right: Results -->
		<div class="results-section glass-panel">
			<h2>Analysis Results</h2>

			{#if errorMsg}
				<div class="alert bg-danger-soft text-danger">
					<strong>Error:</strong> {errorMsg}
				</div>
			{:else if result}
				<div class="result-content animate-fade-in">
					<div class="status-card {result.label === 'correct' ? 'bg-success-soft text-success' : result.label === 'wrong' ? 'bg-warning-soft text-warning' : 'bg-danger-soft text-danger'}">
						<div class="status-header">
							<span class="status-icon">
								{#if result.label === 'correct'}
									<CheckCircle size={28} />
								{:else if result.label === 'wrong'}
									<AlertTriangle size={28} />
								{:else}
									<XCircle size={28} />
								{/if}
							</span>
							<h3>{result.label.toUpperCase()}</h3>
						</div>
						<p class="confidence">Confidence: {(result.confidence * 100).toFixed(1)}%</p>
					</div>

					{#if result.message}
						<div class="feedback-card">
							<h4>Feedback</h4>
							<p>{result.message}</p>
						</div>
					{/if}

					{#if result.elbow_angles}
						<div class="metrics-grid">
							<div class="metric-box">
								<span class="metric-label">Left Elbow</span>
								<span class="metric-value">{result.elbow_angles.left}°</span>
							</div>
							<div class="metric-box">
								<span class="metric-label">Right Elbow</span>
								<span class="metric-value">{result.elbow_angles.right}°</span>
							</div>
						</div>
					{/if}

					{#if result.landmarks}
						<p class="landmark-hint">Skeleton overlay drawn on image.</p>
					{/if}
				</div>
			{:else}
				<div class="empty-results">
					<span class="icon-large opacity-50"><BarChart2 size={48} /></span>
					<p>Upload an image and click analyze to see your results here.</p>
				</div>
			{/if}
		</div>
	</div>
</div>

<style>
	.page-container {
		padding: 2rem;
	}

	.header {
		margin-bottom: 2rem;
		text-align: center;
	}

	.layout-grid {
		grid-template-columns: 1fr 1fr;
		align-items: start;
	}

	@media (max-width: 768px) {
		.page-container {
			padding: 1rem 0;
		}

		.layout-grid {
			grid-template-columns: 1fr;
			gap: 1rem;
		}
		
		.upload-section, .results-section {
			padding: 1rem;
			min-height: auto;
			min-height: 350px;
		}
	}

	.upload-section, .results-section {
		padding: 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
		min-height: 500px;
	}

	.upload-area {
		flex: 1;
		border: 2px dashed var(--surface-border);
		border-radius: var(--radius-md);
		position: relative;
		overflow: hidden;
		display: flex;
		align-items: center;
		justify-content: center;
		background: rgba(0, 0, 0, 0.2);
		transition: var(--transition);
	}

	.upload-area:hover {
		border-color: var(--primary);
	}

	.upload-area.has-image {
		border-style: solid;
	}

	/* Wrapper keeps canvas perfectly aligned to the image */
	.image-wrapper {
		position: relative;
		width: 100%;
		height: 100%;
		min-height: 250px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.preview-image {
		display: block;
		max-width: 100%;
		max-height: 100%;
		object-fit: contain;
	}

	.landmark-canvas {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		pointer-events: none;
		/* Canvas width/height is set in JS; CSS must not distort it */
		max-width: 100%;
		max-height: 100%;
	}

	.upload-overlay {
		position: absolute;
		inset: 0;
		background: rgba(0, 0, 0, 0.6);
		display: flex;
		align-items: center;
		justify-content: center;
		opacity: 0;
		transition: opacity 0.3s ease;
	}

	.upload-area:hover .upload-overlay {
		opacity: 1;
	}

	.empty-state, .empty-results {
		text-align: center;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
		padding: 2rem;
	}

	.icon-large {
		font-size: 3rem;
		margin-bottom: 1rem;
	}

	.opacity-50 { opacity: 0.5; }
	.w-full { width: 100%; }
	.mt-4 { margin-top: 1rem; }

	.alert {
		padding: 1rem;
		border-radius: var(--radius-sm);
	}

	.result-content {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.status-card {
		padding: 1.5rem;
		border-radius: var(--radius-md);
		text-align: center;
	}

	.status-header {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		margin-bottom: 0.5rem;
	}

	.status-header h3 {
		margin: 0;
		font-size: 1.5rem;
	}

	.confidence {
		margin: 0;
		font-size: 0.875rem;
		opacity: 0.8;
	}

	.feedback-card {
		background: rgba(255, 255, 255, 0.05);
		border: 1px solid var(--surface-border);
		padding: 1rem;
		border-radius: var(--radius-sm);
	}

	.feedback-card h4 {
		color: var(--text-muted);
		font-size: 0.875rem;
		text-transform: uppercase;
		letter-spacing: 1px;
	}

	.metrics-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
	}

	.metric-box {
		background: rgba(0, 0, 0, 0.2);
		padding: 1rem;
		border-radius: var(--radius-sm);
		border: 1px solid var(--surface-border);
		display: flex;
		flex-direction: column;
		align-items: center;
	}

	.metric-label {
		font-size: 0.75rem;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 1px;
		margin-bottom: 0.25rem;
	}

	.metric-value {
		font-size: 1.5rem;
		font-weight: 600;
		color: var(--primary);
	}

	.landmark-hint {
		font-size: 0.8rem;
		color: var(--text-muted);
		text-align: center;
		margin: 0;
	}

	.spinner {
		width: 1rem;
		height: 1rem;
		border: 2px solid rgba(255,255,255,0.3);
		border-radius: 50%;
		border-top-color: white;
		animation: spin 1s ease-in-out infinite;
		display: inline-block;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
</style>
