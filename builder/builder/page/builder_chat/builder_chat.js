// Copyright (c) 2025, Frappe Technologies Pvt Ltd and contributors
// For license information, please see license.txt
// Migrated to nora.chat.Progress + nora.chat.Core components

frappe.pages['builder-chat'].on_page_load = function(wrapper) {
	frappe.builder_chat_page = new frappe.ui.BuilderChatPage(wrapper);
};

frappe.pages['builder-chat'].on_page_show = function() {
	if (frappe.builder_chat_page) {
		frappe.builder_chat_page.on_show();
	}
};

/**
 * Builder Chat Page Controller
 * AI-guided conversational interface for site generation.
 * Uses nora.chat.Progress for layout and nora.chat.Core for chat rendering.
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
		this.generation_poll = null;
		this.generation_mode = null;

		// Default step definitions for full-site mode
		this.full_site_steps = [
			{ key: 'description', title: __('Description'), subtitle: __('Business & objective') },
			{ key: 'style', title: __('Style'), subtitle: __('Theme & colors') },
			{ key: 'pages', title: __('Pages'), subtitle: __('Site structure') },
			{ key: 'generation', title: __('Generation'), subtitle: __('Real-time progress') }
		];

		// Step definitions for single-page mode
		this.single_page_steps = [
			{ key: 'page_request', title: __('Page Request'), subtitle: __('Describe your page') },
			{ key: 'generation', title: __('Generation'), subtitle: __('Page creation') }
		];

		this.make();
	}

	make() {
		this.progress = new nora.chat.Progress({
			wrapper: this.page.main,
			title: __('Site Generation'),
			logo: { label: 'NORA' },
			steps: this.full_site_steps,
			action_button: { label: __('Generate Site'), icon: 'fa-magic' },
			chat: {
				bot_name: 'NORA',
				placeholder: __('Describe your website...'),
				enable_upload: true,
				upload_accept: 'image/*'
			}
		});

		// Show loading state in chat area
		this.progress.chat.showLoading(__('Starting conversation...'));

		this.bind_events();
	}

	bind_events() {
		// Chat message send
		this.progress.chat.on('send', ({ message, attachment }) => {
			this.send_message(message);
		});

		// File selected via upload button or drag&drop
		this.progress.chat.on('file_select', ({ file }) => {
			// File is held by NoraChatCore as pending_upload; handled on send
		});

		// Suggestion button clicks
		this.progress.chat.on('button_click', ({ value }) => {
			this.handle_button_click(value);
		});

		// Generate button click
		this.progress.on('action', () => {
			this.trigger_generation();
		});
	}

	on_show() {
		this.start_session();
	}

	// ============ SESSION MANAGEMENT ============

	async start_session() {
		try {
			const response = await frappe.call({
				method: 'builder.api.chat_api.start_session',
				freeze: false
			});

			if (response.message && response.message.success) {
				this.session_id = response.message.session_id;

				// Remove loading, restore input
				this.progress.chat.hideLoading();

				// Display existing messages
				if (response.message.messages && response.message.messages.length > 0) {
					response.message.messages.forEach(msg => {
						if (msg.role !== 'system') {
							this.progress.chat.addMessage(msg.role, msg.content, {
								buttons: msg.buttons || [],
								attachment: msg.attachment || null
							});
						}
					});
				}

				// Update progress
				this.update_progress(response.message);

				// Track generation mode
				if (response.message.generation_mode) {
					this.set_generation_mode(response.message.generation_mode);
				}

				if (response.message.is_resumed) {
					this.progress.chat.addSystemNotice(__('Session resumed. You can continue where you left off.'));
				}

				this.progress.chat.scrollToBottom();
			} else {
				this.progress.chat.showError(
					response.message?.message || __('Failed to start session'),
					() => {
						this.progress.chat.hideLoading();
						this.start_session();
					}
				);
			}
		} catch (error) {
			console.error('Start session error:', error);
			this.progress.chat.showError(
				__('Failed to connect to server'),
				() => {
					this.progress.chat.hideLoading();
					this.start_session();
				}
			);
		}
	}

	// ============ MESSAGING ============

	async send_message(message) {
		if (!message) return;

		// If there is a pending file upload, handle it first
		if (this.progress.chat.pending_upload && this.progress.chat.pending_upload.file) {
			await this.upload_file();
		}

		this.progress.chat.showTyping();

		try {
			const response = await frappe.call({
				method: 'builder.api.chat_api.send_message',
				args: {
					session_id: this.session_id,
					message: message
				},
				freeze: false
			});

			this.progress.chat.hideTyping();

			if (response.message && response.message.success) {
				this.progress.chat.addMessage('assistant', response.message.response, {
					buttons: response.message.buttons || []
				});
				this.update_progress(response.message);
				if (response.message.generation_mode) {
					this.set_generation_mode(response.message.generation_mode);
				}
				this.progress.chat.scrollToBottom();
			} else {
				this.progress.chat.addMessage('assistant',
					response.message?.message || __('Sorry, I encountered an error. Please try again.')
				);
			}
		} catch (error) {
			console.error('Send message error:', error);
			this.progress.chat.hideTyping();
			this.progress.chat.addMessage('assistant', __('Connection error. Please try again.'));
		}
	}

	handle_button_click(value) {
		if (value.startsWith('__')) {
			this.send_special_command(value);
		} else {
			this.progress.chat.setInputValue(value);
			// Trigger send with the value as message
			this.progress.chat.addMessage('user', value);
			this.send_message(value);
		}
	}

	async send_special_command(command) {
		this.progress.chat.showTyping();

		try {
			const response = await frappe.call({
				method: 'builder.api.chat_api.send_message',
				args: {
					session_id: this.session_id,
					message: command
				},
				freeze: false
			});

			this.progress.chat.hideTyping();

			if (response.message && response.message.success) {
				if (response.message.response) {
					this.progress.chat.addMessage('assistant', response.message.response, {
						buttons: response.message.buttons || []
					});
				}
				if (response.message.await_upload) {
					// Trigger file input click
					this.progress.chat.$wrapper.find('.nora-chat-file-input').click();
				}
				if (response.message.generation_mode) {
					this.set_generation_mode(response.message.generation_mode);
				}
				this.update_progress(response.message);
				this.progress.chat.scrollToBottom();
			}
		} catch (error) {
			console.error('Special command error:', error);
			this.progress.chat.hideTyping();
		}
	}

	// ============ FILE UPLOAD ============

	async upload_file() {
		const pending = this.progress.chat.pending_upload;
		if (!pending || !pending.file) return;

		const file = pending.file;
		const attachment_preview = pending.url || URL.createObjectURL(file);

		// Show upload message and typing
		this.progress.chat.addMessage('user', `${__('Logo')}: ${frappe.utils.escape_html(file.name)}`, {
			attachment: attachment_preview
		});
		this.progress.chat.showTyping(__('Uploading logo...'));

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
					method: 'builder.api.chat_api.upload_logo',
					args: {
						session_id: this.session_id,
						file_url: upload_result.message.file_url
					},
					freeze: false
				});

				this.progress.chat.hideTyping();

				if (response.message && response.message.success) {
					this.progress.chat.addMessage('assistant', response.message.response, {
						buttons: response.message.buttons || []
					});
					this.update_progress(response.message);
					this.progress.chat.scrollToBottom();
				} else {
					this.progress.chat.addMessage('assistant',
						response.message?.message || __('Failed to process logo.')
					);
				}
			} else {
				throw new Error('Upload failed');
			}
		} catch (error) {
			console.error('File upload error:', error);
			this.progress.chat.hideTyping();
			this.progress.chat.addMessage('assistant', __('Failed to upload file. Please try again.'));
		}
	}

	// ============ PROGRESS TRACKING ============

	update_progress(data) {
		if (!data) return;

		// Update completion percentage
		const percentage = data.completion_percentage || 0;
		this.progress.updateProgress(percentage);

		// Update current step
		const current_step = data.current_step || 'description';
		this.progress.updateStep(current_step);

		// Update missing fields list
		const missing = data.missing_fields || [];
		if (missing.length === 0 && percentage > 0) {
			this.progress.setMissingFields([
				{ label: __('All required fields completed!'), complete: true }
			]);
		} else {
			this.progress.setMissingFields(
				missing.map(field => ({
					label: field.label || field,
					complete: false
				}))
			);
		}

		// Enable/disable generate button
		const is_ready = data.is_ready || (missing.length === 0 && percentage > 0);
		this.progress.setActionEnabled(is_ready);

		if (is_ready) {
			this.progress.setActionClass('btn-success');
		}
	}

	// ============ GENERATION MODE ============

	set_generation_mode(mode) {
		if (this.generation_mode === mode) return;
		this.generation_mode = mode;

		if (mode === 'single_page') {
			// Rebuild progress panel with single-page steps
			this.progress.steps = this.single_page_steps;
			this.progress.render();
			this.rebind_after_render();
			this.progress.setActionLabel(__('Generate Page'), 'fa-magic');
			this.progress.$progress_panel.find('.progress-header h4')
				.text(__('Page Generation'));
		}
	}

	/**
	 * After re-rendering the progress component (e.g. mode change),
	 * re-bind chat events since the chat instance is recreated.
	 */
	rebind_after_render() {
		this.bind_events();
	}

	// ============ GENERATION ============

	async trigger_generation() {
		const is_single = this.generation_mode === 'single_page';
		const btn_label = is_single ? __('Generate Page') : __('Generate Site');

		this.progress.setActionEnabled(false);
		this.progress.setActionLabel(__('Starting...'), 'fa-spinner fa-spin');

		this.progress.chat.addMessage('assistant',
			is_single
				? `**${__('Generating page...')}**\n\n${__('This should only take a moment.')}`
				: `**${__('Starting site generation...')}**\n\n${__('This may take a few minutes. I will show you the progress in real-time.')}`
		);

		try {
			const response = await frappe.call({
				method: 'builder.api.chat_api.trigger_generation',
				args: { session_id: this.session_id },
				freeze: false
			});

			if (response.message && response.message.success) {
				// Check if generation completed synchronously (single page mode)
				if (response.message.status === 'completed') {
					this.on_generation_complete(response.message);
					return;
				}

				// Full site: update step and start polling
				this.update_progress({
					current_step: 'generation',
					completion_percentage: response.message.completion_percentage || 0,
					missing_fields: []
				});

				this.start_generation_polling(response.message.job_id);
			} else {
				this.progress.setActionEnabled(true);
				this.progress.setActionLabel(btn_label, 'fa-magic');
				this.progress.chat.addMessage('assistant',
					response.message?.message || __('Failed to start generation. Please try again.')
				);
			}
		} catch (error) {
			console.error('Trigger generation error:', error);
			this.progress.setActionEnabled(true);
			this.progress.setActionLabel(btn_label, 'fa-magic');
			this.progress.chat.addMessage('assistant', __('Connection error. Please try again.'));
		}
	}

	start_generation_polling(job_id) {
		this.progress.setActionLabel(__('Generating...'), 'fa-spinner fa-spin');

		// Disable chat input during generation
		this.progress.chat.setInputDisabled(true);

		let last_page = null;

		this.generation_poll = setInterval(async () => {
			try {
				const response = await frappe.call({
					method: 'builder.api.chat_api.get_generation_status',
					args: { session_id: this.session_id },
					freeze: false
				});

				if (!response.message) return;

				const status = response.message;

				// Update progress bar
				const gen_progress = status.progress || 0;
				this.progress.updateProgress(gen_progress);

				// Show page progress as system notice
				if (status.current_page && status.current_page !== last_page) {
					last_page = status.current_page;
					this.progress.chat.addSystemNotice(
						`${__('Generating page')}: ${frappe.utils.escape_html(status.current_page)} (${status.pages_created?.length || 0}/${status.total_pages || '?'})`
					);
					this.progress.chat.scrollToBottom();
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
		this.progress.updateProgress(100);

		this.progress.setActionLabel(__('Completed!'), 'fa-check');
		this.progress.setActionClass('btn-success');

		// Build page links
		const pages = status.pages_created || [];
		const is_single = this.generation_mode === 'single_page';
		let page_list = pages.map(p => `- [${p.title || p.page_name}](/builder/page/${p.page_name})`).join('\n');

		this.progress.chat.addMessage('assistant',
			is_single
				? `**${__('Page generated successfully!')}**\n\n`
				  + `${page_list}\n\n`
				  + `${__('You can now edit your page in the Builder editor.')}`
				: `**${__('Site generated successfully!')}**\n\n`
				  + `${__('Pages created')}:\n${page_list}\n\n`
				  + `${__('You can now edit your pages in the Builder editor.')}`
		);

		// Mark generation step as completed
		this.progress.updateStep('generation');
		// Manually mark it as completed (all steps before should already be)
		const $gen_step = this.progress.$progress_panel.find('.nora-chat-step[data-step="generation"]');
		$gen_step.removeClass('active').addClass('completed');
		$gen_step.find('.nora-chat-step-indicator').html('<i class="fa fa-check"></i>');
		$gen_step.find('.nora-chat-step-status').html('<i class="fa fa-check" style="color: #48bb78;"></i>');

		// Re-enable chat input
		this.progress.chat.setInputDisabled(false);
		this.progress.chat.scrollToBottom();
	}

	on_generation_failed(status) {
		const is_single = this.generation_mode === 'single_page';
		const btn_label = is_single ? __('Generate Page') : __('Retry Generation');

		this.progress.setActionEnabled(true);
		this.progress.setActionLabel(btn_label, 'fa-magic');

		// Re-enable chat input
		this.progress.chat.setInputDisabled(false);

		this.progress.chat.addMessage('assistant',
			`**${__('Generation failed')}**\n\n${status.error || __('An unexpected error occurred. Please try again.')}`
		);

		this.progress.chat.scrollToBottom();
	}
};
