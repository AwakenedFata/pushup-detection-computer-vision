<script>
	import { Sparkles, Camera, Image, Zap, Target, Ruler } from "lucide-svelte";
</script>

<svelte:head>
	<title>PushupPro | AI Posture Detection</title>
	<meta
		name="description"
		content="Master your pushup form with advanced AI posture detection powered by MediaPipe and FastAPI."
	/>
</svelte:head>

<div class="hero-section">
	<div class="container hero-content animate-fade-in">
		<div class="badge glass-panel">
			<Sparkles
				size={16}
				style="display:inline; vertical-align:middle; margin-right:4px;"
			/> Computer Vision Final Project
		</div>

		<h1 class="hero-title">
			Perfect Your Form with <br />
			<span class="text-gradient">Posture Analysis</span>
		</h1>

		<p class="hero-subtitle">
			Leveraging MediaPipe Tasks API and a custom Machine Learning
			classifier to evaluate your pushup technique in real-time. Stop
			counting bad reps.
		</p>

		<div class="hero-actions">
			<a href="/predict/realtime" class="btn btn-primary btn-lg">
				<span class="icon"><Camera size={20} /></span> Start Real-time Tracker
			</a>
			<a href="/predict/image" class="btn btn-secondary btn-lg">
				<span class="icon"><Image size={20} /></span> Upload Image
			</a>
		</div>
	</div>

	<div class="features-grid container">
		<div
			class="feature-card glass-panel animate-fade-in"
			style="animation-delay: 0.1s"
		>
			<div class="feature-icon bg-primary-soft text-primary">
				<Zap size={24} />
			</div>
			<h3>Real-time Tracking</h3>
			<p>
				Get instant feedback on your form via webcam using blazing fast
				WebSocket streaming.
			</p>
		</div>
		<div
			class="feature-card glass-panel animate-fade-in"
			style="animation-delay: 0.2s"
		>
			<div class="feature-icon bg-success-soft text-success">
				<Target size={24} />
			</div>
			<h3>Smart Rep Counting</h3>
			<p>
				Our algorithm tracks your elbow angles to count only the
				repetitions with proper depth.
			</p>
		</div>
		<div
			class="feature-card glass-panel animate-fade-in"
			style="animation-delay: 0.3s"
		>
			<div class="feature-icon bg-warning-soft text-warning">
				<Ruler size={24} />
			</div>
			<h3>Posture Alignment</h3>
			<p>
				Detects misalignments in your hips and back to prevent injuries
				and maximize gains.
			</p>
		</div>
	</div>
</div>

<style>
	.hero-section {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 4rem 0;
		position: relative;
		overflow: hidden;
	}

	.hero-section::before {
		content: "";
		position: absolute;
		top: -20%;
		left: -10%;
		width: 50%;
		height: 50%;
		background: radial-gradient(
			circle,
			rgba(59, 130, 246, 0.2) 0%,
			transparent 70%
		);
		z-index: -1;
		filter: blur(40px);
	}

	.hero-content {
		text-align: center;
		max-width: 800px;
		margin-bottom: 5rem;
	}

	.badge {
		display: inline-block;
		padding: 0.5rem 1rem;
		border-radius: var(--radius-full);
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--primary);
		margin-bottom: 2rem;
		border-color: rgba(59, 130, 246, 0.3);
		background: rgba(59, 130, 246, 0.1);
	}

	.hero-title {
		font-size: 4rem;
		font-weight: 700;
		line-height: 1.1;
		margin-bottom: 1.5rem;
		letter-spacing: -1px;
	}

	.text-gradient {
		background: linear-gradient(135deg, #3b82f6, #10b981);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
	}

	.hero-subtitle {
		font-size: 1.25rem;
		color: var(--text-muted);
		margin-bottom: 2.5rem;
		max-width: 600px;
		margin-inline: auto;
	}

	.hero-actions {
		display: flex;
		gap: 1.5rem;
		justify-content: center;
	}

	.btn-lg {
		padding: 1rem 2rem;
		font-size: 1.125rem;
	}

	.icon {
		font-size: 1.25rem;
	}

	.features-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
		gap: 2rem;
		width: 100%;
	}

	.feature-card {
		padding: 2rem;
		text-align: left;
		transition:
			transform 0.3s ease,
			box-shadow 0.3s ease;
	}

	.feature-card:hover {
		transform: translateY(-5px);
		box-shadow: var(--shadow-glow);
		border-color: rgba(59, 130, 246, 0.3);
	}

	.feature-icon {
		width: 48px;
		height: 48px;
		border-radius: 12px;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 1.5rem;
		margin-bottom: 1.5rem;
	}

	.bg-primary-soft {
		background: rgba(59, 130, 246, 0.1);
		border: 1px solid rgba(59, 130, 246, 0.2);
	}
	.bg-success-soft {
		background: rgba(16, 185, 129, 0.1);
		border: 1px solid rgba(16, 185, 129, 0.2);
	}
	.bg-warning-soft {
		background: rgba(245, 158, 11, 0.1);
		border: 1px solid rgba(245, 158, 11, 0.2);
	}

	@media (max-width: 768px) {
		.hero-title {
			font-size: 2.5rem;
		}
		.hero-actions {
			flex-direction: column;
		}
	}
</style>
