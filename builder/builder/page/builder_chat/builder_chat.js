// Copyright (c) 2025, Frappe Technologies Pvt Ltd and contributors
// For license information, please see license.txt

frappe.pages['builder-chat'].on_page_load = function(wrapper) {
	// Hide Frappe UI elements for full-screen chat experience
	const hideElements = () => {
		$('.page-head').hide();
		$('.page-head-content').hide();
		$('.sticky-top').hide();
		$('.body-sidebar-container').hide();
		$('#body_sidebar').hide();
		$('.layout-side-section').hide();
		$(wrapper).find('.page-head').hide();
		$(wrapper).closest('.page-container').find('.page-head').hide();
		$('.main-section').css({
			'margin-left': '0',
			'width': '100%'
		});
	};

	hideElements();
	setTimeout(hideElements, 100);
	setTimeout(hideElements, 500);

	frappe.builder_chat_page = new frappe.ui.BuilderChatPage(wrapper);
};

frappe.pages['builder-chat'].on_page_show = function() {
	if (frappe.builder_chat_page) {
		frappe.builder_chat_page.on_show();
	}
};

/**
 * Builder Chat Page Controller
 * AI-guided conversational interface for site generation
 */
frappe.ui.BuilderChatPage = class BuilderChatPage {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __('Builder AI Chat'),
			single_column: false
		});

		this.session_id = null;
		this.is_typing = false;
		this.pending_upload = null;
		this.generation_poll = null;

		this.make();
	}

	make() {
		this.page.main.html(`
			<div class="builder-chat-container">
				<!-- Progress Panel (Left) -->
				<div class="builder-progress-panel">
					<div class="progress-header">
						<div class="builder-logo">
							<svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
								<rect x="3" y="3" width="8" height="8" rx="2" fill="rgba(255,255,255,0.9)"/>
								<rect x="13" y="3" width="8" height="8" rx="2" fill="rgba(255,255,255,0.6)"/>
								<rect x="3" y="13" width="8" height="8" rx="2" fill="rgba(255,255,255,0.6)"/>
								<rect x="13" y="13" width="8" height="8" rx="2" fill="rgba(255,255,255,0.3)"/>
							</svg>
							<span>Builder AI</span>
						</div>
						<h4>${__('Site Generation')}</h4>
					</div>

					<!-- Steps -->
					<div class="builder-steps">
						<div class="builder-step active" data-step="description">
							<div class="step-indicator">1</div>
							<div class="step-info">
								<div class="step-title">${__('Description')}</div>
								<div class="step-subtitle">${__('Business & objective')}</div>
							</div>
							<div class="step-status">
								<i class="fa fa-spinner fa-spin"></i>
							</div>
						</div>
						<div class="builder-step" data-step="style">
							<div class="step-indicator">2</div>
							<div class="step-info">
								<div class="step-title">${__('Style')}</div>
								<div class="step-subtitle">${__('Theme & colors')}</div>
							</div>
							<div class="step-status">
								<i class="fa fa-circle-o"></i>
							</div>
						</div>
						<div class="builder-step" data-step="pages">
							<div class="step-indicator">3</div>
							<div class="step-info">
								<div class="step-title">${__('Pages')}</div>
								<div class="step-subtitle">${__('Site structure')}</div>
							</div>
							<div class="step-status">
								<i class="fa fa-circle-o"></i>
							</div>
						</div>
						<div class="builder-step" data-step="generation">
							<div class="step-indicator">4</div>
							<div class="step-info">
								<div class="step-title">${__('Generation')}</div>
								<div class="step-subtitle">${__('Real-time progress')}</div>
							</div>
							<div class="step-status">
								<i class="fa fa-circle-o"></i>
							</div>
						</div>
					</div>

					<!-- Progress Bar -->
					<div class="progress-bar-container">
						<div class="progress-bar">
							<div class="progress-fill" style="width: 0%"></div>
						</div>
						<div class="progress-text">0%</div>
					</div>

					<!-- Missing Fields -->
					<div class="missing-fields-container">
						<h5>${__('Required Information')}</h5>
						<ul class="missing-fields-list">
							<li class="loading">${__('Loading...')}</li>
						</ul>
					</div>

					<!-- Generate Button -->
					<div class="generate-container">
						<button class="btn btn-primary btn-generate" disabled>
							<i class="fa fa-magic"></i>
							${__('Generate Site')}
						</button>
					</div>
				</div>

				<!-- Chat Area (Right) -->
				<div class="builder-chat-area">
					<!-- Messages Container -->
					<div class="chat-messages">
						<div class="chat-loading">
							<i class="fa fa-spinner fa-spin"></i>
							<span>${__('Starting conversation...')}</span>
						</div>
					</div>

					<!-- Input Area -->
					<div class="chat-input-area">
						<!-- File Upload Zone -->
						<div class="file-upload-zone" style="display: none;">
							<div class="upload-preview">
								<img src="" alt="Preview" />
								<span class="filename"></span>
								<button class="btn btn-xs btn-danger remove-file">
									<i class="fa fa-times"></i>
								</button>
							</div>
						</div>

						<!-- Input Row -->
						<div class="chat-input-row">
							<button class="btn btn-default btn-upload" title="${__('Upload logo')}">
								<i class="fa fa-image"></i>
							</button>
							<textarea class="chat-input" placeholder="${__('Describe your website...')}" rows="1"></textarea>
							<button class="btn btn-primary btn-send" disabled>
								<i class="fa fa-paper-plane"></i>
							</button>
						</div>

						<!-- Hidden file input -->
						<input type="file" class="file-input" accept="image/*" style="display: none;" />
					</div>
				</div>
			</div>
		`);

		this.setup_elements();
		this.bind_events();
	}

	setup_elements() {
		this.$container = this.page.main.find('.builder-chat-container');
		this.$progress_panel = this.$container.find('.builder-progress-panel');
		this.$chat_area = this.$container.find('.builder-chat-area');
		this.$messages = this.$container.find('.chat-messages');
		this.$input = this.$container.find('.chat-input');
		this.$send_btn = this.$container.find('.btn-send');
		this.$upload_btn = this.$container.find('.btn-upload');
		this.$file_input = this.$container.find('.file-input');
		this.$upload_zone = this.$container.find('.file-upload-zone');
		this.$generate_btn = this.$container.find('.btn-generate');
		this.$progress_fill = this.$container.find('.progress-fill');
		this.$progress_text = this.$container.find('.progress-text');
		this.$missing_list = this.$container.find('.missing-fields-list');
		this.$steps = this.$container.find('.builder-step');
	}

	bind_events() {
		// Send message on button click
		this.$send_btn.on('click', () => this.send_message());

		// Send message on Enter (Shift+Enter for newline)
		this.$input.on('keydown', (e) => {
			if (e.key === 'Enter' && !e.shiftKey) {
				e.preventDefault();
				this.send_message();
			}
		});

		// Enable/disable send button based on input
		this.$input.on('input', () => {
			const has_text = this.$input.val().trim().length > 0;
			const has_file = this.pending_upload !== null;
			this.$send_btn.prop('disabled', !has_text && !has_file);

			// Auto-resize textarea
			this.$input[0].style.height = 'auto';
			this.$input[0].style.height = Math.min(this.$input[0].scrollHeight, 120) + 'px';
		});

		// File upload button
		this.$upload_btn.on('click', () => this.$file_input.click());

		// File selection
		this.$file_input.on('change', (e) => this.handle_file_select(e));

		// Remove file button
		this.$upload_zone.find('.remove-file').on('click', () => this.clear_pending_upload());

		// Drag and drop
		this.$chat_area.on('dragover', (e) => {
			e.preventDefault();
			this.$chat_area.addClass('drag-over');
		});

		this.$chat_area.on('dragleave', () => {
			this.$chat_area.removeClass('drag-over');
		});

		this.$chat_area.on('drop', (e) => {
			e.preventDefault();
			this.$chat_area.removeClass('drag-over');
			const files = e.originalEvent.dataTransfer.files;
			if (files.length > 0) {
				this.handle_file(files[0]);
			}
		});

		// Generate button
		this.$generate_btn.on('click', () => this.trigger_generation());

		// Delegate click on suggestion buttons
		this.$messages.on('click', '.suggestion-btn', (e) => {
			const value = $(e.currentTarget).data('value');
			this.handle_button_click(value);
		});
	}

	on_show() {
		this.start_session();
	}

	async start_session() {
		try {
			const response = await frappe.call({
				method: 'builder.api.chat_start_session',
				freeze: false
			});

			if (response.message && response.message.success) {
				this.session_id = response.message.session_id;
				this.$messages.find('.chat-loading').remove();

				// Display existing messages
				if (response.message.messages && response.message.messages.length > 0) {
					response.message.messages.forEach(msg => {
						if (msg.role !== 'system') {
							this.add_message(msg.role, msg.content, msg.buttons, msg.attachment);
						}
					});
				}

				// Update progress
				this.update_progress({
					current_step: response.message.current_step,
					completion_percentage: response.message.completion_percentage,
					missing_fields: response.message.missing_fields
				});

				if (response.message.is_resumed) {
					this.add_system_notice(__('Session resumed. You can continue where you left off.'));
				}

				this.scroll_to_bottom();
			} else {
				this.show_error(response.message?.message || __('Failed to start session'));
			}
		} catch (error) {
			console.error('Start session error:', error);
			this.show_error(__('Failed to connect to server'));
		}
	}

	async send_message() {
		const message = this.$input.val().trim();

		if (!message && !this.pending_upload) return;

		// Clear input
		this.$input.val('');
		this.$input.css('height', 'auto');
		this.$send_btn.prop('disabled', true);

		// Handle file upload if pending
		if (this.pending_upload) {
			await this.upload_file();
			if (!message) return;
		}

		// Add user message to UI
		this.add_message('user', message);
		this.show_typing();

		try {
			const response = await frappe.call({
				method: 'builder.api.chat_send_message',
				args: {
					session_id: this.session_id,
					message: message
				},
				freeze: false
			});

			this.hide_typing();

			if (response.message && response.message.success) {
				this.add_message('assistant', response.message.response, response.message.buttons);
				this.update_progress(response.message);
				this.scroll_to_bottom();
			} else {
				this.add_message('assistant', response.message?.message || __('Sorry, I encountered an error. Please try again.'));
			}
		} catch (error) {
			console.error('Send message error:', error);
			this.hide_typing();
			this.add_message('assistant', __('Connection error. Please try again.'));
		}
	}

	handle_file_select(e) {
		const file = e.target.files[0];
		if (file) this.handle_file(file);
		this.$file_input.val('');
	}

	handle_file(file) {
		const valid_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/svg+xml'];
		if (!valid_types.includes(file.type)) {
			frappe.msgprint(__('Please upload a PNG, JPEG, or SVG image.'));
			return;
		}

		if (file.size > 5 * 1024 * 1024) {
			frappe.msgprint(__('File size must be less than 5MB.'));
			return;
		}

		this.pending_upload = file;

		// Show preview
		if (file.type.startsWith('image/') && file.type !== 'image/svg+xml') {
			const reader = new FileReader();
			reader.onload = (e) => {
				this.$upload_zone.find('img').attr('src', e.target.result).show();
			};
			reader.readAsDataURL(file);
		} else {
			this.$upload_zone.find('img').hide();
		}

		this.$upload_zone.find('.filename').text(file.name);
		this.$upload_zone.show();
		this.$send_btn.prop('disabled', false);
	}

	clear_pending_upload() {
		this.pending_upload = null;
		this.$upload_zone.hide();
		this.$upload_zone.find('img').attr('src', '').hide();
		this.$upload_zone.find('.filename').text('');

		const has_text = this.$input.val().trim().length > 0;
		this.$send_btn.prop('disabled', !has_text);
	}

	async upload_file() {
		if (!this.pending_upload) return;

		const file = this.pending_upload;
		this.clear_pending_upload();

		const attachment_preview = URL.createObjectURL(file);
		this.add_message('user', `${__('Logo')}: ${file.name}`, null, attachment_preview);
		this.show_typing(__('Uploading logo...'));

		try {
			const formData = new FormData();
			formData.append('file', file);

			const upload_response = await fetch('/api/method/upload_file', {
				method: 'POST',
				body: formData,
				headers: {
					'X-Frappe-CSRF-Token': frappe.csrf_token
				}
			});

			const upload_result = await upload_response.json();

			if (upload_result.message && upload_result.message.file_url) {
				const response = await frappe.call({
					method: 'builder.api.chat_upload_logo',
					args: {
						session_id: this.session_id,
						file_url: upload_result.message.file_url
					},
					freeze: false
				});

				this.hide_typing();

				if (response.message && response.message.success) {
					this.add_message('assistant', response.message.response, response.message.buttons);
					this.update_progress(response.message);
					this.scroll_to_bottom();
				} else {
					this.add_message('assistant', response.message?.message || __('Failed to process logo.'));
				}
			} else {
				throw new Error('Upload failed');
			}
		} catch (error) {
			console.error('File upload error:', error);
			this.hide_typing();
			this.add_message('assistant', __('Failed to upload file. Please try again.'));
		}
	}

	handle_button_click(value) {
		if (value.startsWith('__')) {
			this.send_special_command(value);
		} else {
			this.$input.val(value);
			this.send_message();
		}
	}

	async send_special_command(command) {
		this.show_typing();

		try {
			const response = await frappe.call({
				method: 'builder.api.chat_send_message',
				args: {
					session_id: this.session_id,
					message: command
				},
				freeze: false
			});

			this.hide_typing();

			if (response.message && response.message.success) {
				if (response.message.response) {
					this.add_message('assistant', response.message.response, response.message.buttons);
				}
				if (response.message.await_upload) {
					this.$file_input.click();
				}
				this.update_progress(response.message);
				this.scroll_to_bottom();
			}
		} catch (error) {
			console.error('Special command error:', error);
			this.hide_typing();
		}
	}

	add_message(role, content, buttons = null, attachment = null) {
		const is_user = role === 'user';
		const avatar = is_user
			? frappe.get_gravatar(frappe.session.user_email)
			: '/assets/builder/images/builder-bot.svg';

		let formatted_content = this.format_content(content);

		let html = `
			<div class="chat-message ${is_user ? 'user-message' : 'assistant-message'}">
				<div class="message-avatar">
					<img src="${avatar}" alt="${role}" onerror="this.src='/assets/frappe/images/default-avatar.png'" />
				</div>
				<div class="message-content">
					${attachment && attachment.startsWith('blob:') ? `<img src="${attachment}" class="message-attachment" alt="Uploaded file" />` : ''}
					<div class="message-text">${formatted_content}</div>
					${buttons ? this.render_buttons(buttons) : ''}
				</div>
			</div>
		`;

		this.$messages.append(html);
	}

	format_content(content) {
		if (!content) return '';

		if (typeof marked !== 'undefined') {
			marked.setOptions({
				breaks: true,
				gfm: true,
				sanitize: false
			});
			return marked.parse(content);
		}

		// Fallback: basic markdown support
		let result = frappe.utils.escape_html(content);
		result = result.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
		result = result.replace(/\*([^*]+)\*/g, '<em>$1</em>');
		result = result.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
		result = result.replace(/\n/g, '<br>');
		return result;
	}

	render_buttons(buttons) {
		if (!buttons || !Array.isArray(buttons)) return '';

		const btns = buttons.map(btn => {
			return `<button class="btn btn-sm btn-default suggestion-btn" data-value="${frappe.utils.escape_html(btn.value)}">${frappe.utils.escape_html(btn.label)}</button>`;
		}).join('');

		return `<div class="suggestion-buttons">${btns}</div>`;
	}

	add_system_notice(text) {
		this.$messages.append(`
			<div class="chat-system-notice">
				<i class="fa fa-info-circle"></i>
				<span>${text}</span>
			</div>
		`);
	}

	show_typing(text = null) {
		if (this.is_typing) return;
		this.is_typing = true;

		this.$messages.append(`
			<div class="chat-message assistant-message typing-indicator">
				<div class="message-avatar">
					<img src="/assets/builder/images/builder-bot.svg" alt="Assistant" onerror="this.src='/assets/frappe/images/default-avatar.png'" />
				</div>
				<div class="message-content">
					<div class="typing-dots">
						<span></span>
						<span></span>
						<span></span>
					</div>
					${text ? `<span class="typing-text">${text}</span>` : ''}
				</div>
			</div>
		`);

		this.scroll_to_bottom();
	}

	hide_typing() {
		this.is_typing = false;
		this.$messages.find('.typing-indicator').remove();
	}

	show_error(message) {
		this.$messages.find('.chat-loading').remove();
		this.$messages.append(`
			<div class="chat-error">
				<i class="fa fa-exclamation-triangle"></i>
				<span>${message}</span>
				<button class="btn btn-sm btn-default retry-btn">${__('Retry')}</button>
			</div>
		`);

		this.$messages.find('.retry-btn').on('click', () => {
			this.$messages.find('.chat-error').remove();
			this.start_session();
		});
	}

	update_progress(data) {
		if (!data) return;

		// Update completion percentage
		const percentage = data.completion_percentage || 0;
		this.$progress_fill.css('width', `${percentage}%`);
		this.$progress_text.text(`${Math.round(percentage)}%`);

		if (percentage >= 80) {
			this.$progress_fill.addClass('high');
		} else {
			this.$progress_fill.removeClass('high');
		}

		// Update current step
		const current_step = data.current_step || 'description';
		this.$steps.removeClass('active completed');

		this.$steps.each((i, el) => {
			const $step = $(el);
			const step_name = $step.data('step');

			if (step_name === current_step) {
				$step.addClass('active');
				$step.find('.step-status i').attr('class', 'fa fa-spinner fa-spin');
			} else if (this.is_step_before(step_name, current_step)) {
				$step.addClass('completed');
				$step.find('.step-status i').attr('class', 'fa fa-check');
			} else {
				$step.find('.step-status i').attr('class', 'fa fa-circle-o');
			}
		});

		// Update missing fields list
		const missing = data.missing_fields || [];
		this.$missing_list.empty();

		if (missing.length === 0) {
			this.$missing_list.append(`<li class="complete"><i class="fa fa-check"></i> ${__('All required fields completed!')}</li>`);
		} else {
			missing.forEach(field => {
				this.$missing_list.append(`<li class="missing"><i class="fa fa-times"></i> ${field.label}</li>`);
			});
		}

		// Enable/disable generate button
		const is_ready = data.is_ready || (missing.length === 0 && percentage > 0);
		this.$generate_btn.prop('disabled', !is_ready);

		if (is_ready) {
			this.$generate_btn.removeClass('btn-primary').addClass('btn-success');
		} else {
			this.$generate_btn.removeClass('btn-success').addClass('btn-primary');
		}
	}

	is_step_before(step, current) {
		const order = ['description', 'style', 'pages', 'generation'];
		return order.indexOf(step) < order.indexOf(current);
	}

	async trigger_generation() {
		if (this.$generate_btn.prop('disabled')) return;

		this.$generate_btn.prop('disabled', true).html(
			`<i class="fa fa-spinner fa-spin"></i> ${__('Starting...')}`
		);

		this.add_message('assistant',
			`**${__('Starting site generation...')}**\n\n${__('This may take a few minutes. I will show you the progress in real-time.')}`
		);

		try {
			const response = await frappe.call({
				method: 'builder.api.chat_trigger_generation',
				args: { session_id: this.session_id },
				freeze: false
			});

			if (response.message && response.message.success) {
				// Update step to generation
				this.update_progress({
					current_step: 'generation',
					completion_percentage: response.message.completion_percentage || 0,
					missing_fields: []
				});

				// Start polling for generation status
				this.start_generation_polling(response.message.job_id);
			} else {
				this.$generate_btn.prop('disabled', false).html(
					`<i class="fa fa-magic"></i> ${__('Generate Site')}`
				);
				this.add_message('assistant',
					response.message?.message || __('Failed to start generation. Please try again.')
				);
			}
		} catch (error) {
			console.error('Trigger generation error:', error);
			this.$generate_btn.prop('disabled', false).html(
				`<i class="fa fa-magic"></i> ${__('Generate Site')}`
			);
			this.add_message('assistant', __('Connection error. Please try again.'));
		}
	}

	start_generation_polling(job_id) {
		this.$generate_btn.html(
			`<i class="fa fa-spinner fa-spin"></i> ${__('Generating...')}`
		);

		// Disable chat input during generation
		this.$input.prop('disabled', true);
		this.$send_btn.prop('disabled', true);

		let last_page = null;

		this.generation_poll = setInterval(async () => {
			try {
				const response = await frappe.call({
					method: 'builder.api.chat_get_generation_status',
					args: { session_id: this.session_id },
					freeze: false
				});

				if (!response.message) return;

				const status = response.message;

				// Update progress bar
				const progress = status.progress || 0;
				this.$progress_fill.css('width', `${progress}%`);
				this.$progress_text.text(`${Math.round(progress)}%`);

				// Show page progress
				if (status.current_page && status.current_page !== last_page) {
					last_page = status.current_page;
					this.add_system_notice(
						`${__('Generating page')}: ${status.current_page} (${status.pages_created?.length || 0}/${status.total_pages || '?'})`
					);
					this.scroll_to_bottom();
				}

				// Check completion
				if (status.status === 'completed') {
					this.stop_generation_polling();
					this.on_generation_complete(status);
				} else if (status.status === 'failed') {
					this.stop_generation_polling();
					this.on_generation_failed(status);
				}
			} catch (error) {
				console.error('Generation polling error:', error);
			}
		}, 3000);
	}

	stop_generation_polling() {
		if (this.generation_poll) {
			clearInterval(this.generation_poll);
			this.generation_poll = null;
		}
	}

	on_generation_complete(status) {
		this.$progress_fill.css('width', '100%').addClass('high');
		this.$progress_text.text('100%');

		this.$generate_btn.html(
			`<i class="fa fa-check"></i> ${__('Completed!')}`
		).removeClass('btn-primary btn-success').addClass('btn-success');

		// Build page links
		const pages = status.pages_created || [];
		let page_list = pages.map(p => `- [${p.title || p.page_name}](/builder/page/${p.page_name})`).join('\n');

		this.add_message('assistant',
			`**${__('Site generated successfully!')}**\n\n` +
			`${__('Pages created')}:\n${page_list}\n\n` +
			`${__('You can now edit your pages in the Builder editor.')}`
		);

		// Mark step as completed
		this.$steps.filter('[data-step="generation"]').addClass('completed')
			.find('.step-status i').attr('class', 'fa fa-check');

		this.scroll_to_bottom();
	}

	on_generation_failed(status) {
		this.$generate_btn.prop('disabled', false).html(
			`<i class="fa fa-magic"></i> ${__('Retry Generation')}`
		);

		// Re-enable chat input
		this.$input.prop('disabled', false);

		this.add_message('assistant',
			`**${__('Generation failed')}**\n\n${status.error || __('An unexpected error occurred. Please try again.')}`
		);

		this.scroll_to_bottom();
	}

	scroll_to_bottom() {
		setTimeout(() => {
			this.$messages.scrollTop(this.$messages[0].scrollHeight);
		}, 100);
	}
};
