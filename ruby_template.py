# -*- coding: utf-8 -*-
"""
Embedded Ruby script template for SketchUp pipeline automation.
"""

RUBY_BRIDGE_CODE = r'''
begin
  require 'json'
  
  CONFIG_FILE = "{{CONFIG_PATH}}"
  STATUS_FILE = "{{STATUS_PATH}}"
  LOG_FILE    = "{{LOG_PATH}}"
  
  def self.log(msg)
    puts "[PIPELINE] #{msg}"
    File.open(LOG_FILE, "a") { |f| f.puts "[#{Time.now.strftime('%H:%M:%S')}] #{msg}" } rescue nil
  end

  def self.update_status(status, progress, message, extra = {})
    log(message)
    data = {
      "status" => status,
      "progress" => progress,
      "message" => message,
      "timestamp" => Time.now.to_i
    }.merge(extra)
    
    File.open(STATUS_FILE, "w") do |f|
      f.write(JSON.dump(data))
    end rescue nil
  end

  def self.classify_entity(e)
    return :architecture if e.is_a?(Sketchup::SectionPlane)
    return :stray if e.is_a?(Sketchup::Edge)
    return :architecture if e.is_a?(Sketchup::Dimension) || e.is_a?(Sketchup::Text)
    
    tag_name = (e.layer ? e.layer.name : "").downcase
    name = (e.name rescue "").downcase
    def_name = ""
    if e.is_a?(Sketchup::Group)
      def_name = (e.definition.name rescue "").downcase
    elsif e.is_a?(Sketchup::ComponentInstance)
      def_name = (e.definition.name rescue "").downcase
    end
    
    text = "#{tag_name} #{name} #{def_name}"
    
    # Vegetation patterns
    if text =~ /paisag|veg|plant|arvor|jardim|flor|grama|tree|leaf|leaves|folha|hojas|bamboo|aglaonema|vaso|palmeira|bush|grass|pot|floreira|verde/i
      return :furniture_vegetation
    end
    
    # Furniture & equipment patterns
    if text =~ /mob|furn|decor|equip|fit|acad|cross|pilat|reformer|cadillac|espaldar|kettlebell|halter|peso|anilha|rack|banco|chair|cadeira|mesa|table|sofa|poltrona|armario|estante|puff|balcao|tv|espelho|persiana|ventilador|dicroica|luminaria|arandela|pendente|aparelho|esteira|bike|box|banqueta|cesto|basket|quadro|escrivaninha|colch/i
      return :furniture_vegetation
    end
    
    # Architecture patterns
    if text =~ /arq|alvenaria|parede|piso|laje|forro|teto|cobertura|telhado|estrutura|esquadria|porta|janela|vidro|wall|floor|roof|ceiling|door|window|slab|viga|pilar|shaft|terreno|calcada|edifica|weiku/i
      return :architecture
    end
    
    # Bounding box heuristics
    bb = e.bounds rescue nil
    if bb
      w = bb.width * 2.54
      h = bb.height * 2.54
      d = bb.depth * 2.54
      max_dim = [w, h].max
      
      # Large horizontal objects (> 9 meters) are almost always slabs, roofs, floors, ceilings or site terrain
      return :architecture if max_dim > 900.0
      
      # Large wall-like objects (> 5m long and > 2m high)
      return :architecture if max_dim > 500.0 && d > 180.0
    end
    
    # Default fallback for interior elements
    :furniture_vegetation
  end

  def self.purge_all(model)
    3.times do
      model.definitions.purge_unused rescue nil
      model.materials.purge_unused rescue nil
      model.layers.purge_unused rescue nil
      model.styles.purge_unused rescue nil
    end
  end

  $pipeline_executed = false

  def self.run_pipeline(model)
    return if $pipeline_executed
    $pipeline_executed = true
    
    begin
      update_status("running", 15, "Lendo configuracoes e analisando modelo...")
      cfg = JSON.parse(File.read(CONFIG_FILE))
      
      source_path = cfg["source_skp"]
      dir = File.dirname(source_path)
      base_name = File.basename(source_path, ".*")
      
      opt_path  = "#{dir}/#{base_name}_Otimizado.skp"
      arch_path = "#{dir}/#{base_name}_Arquitetura.skp"
      mob_path  = "#{dir}/#{base_name}_Assets.skp"
      
      all_ents = model.entities.to_a
      update_status("running", 25, "Classificando #{all_ents.count} entidades...")
      
      arch_pids = []
      mob_pids = []
      stray_ents = []
      
      all_ents.each do |e|
        cat = classify_entity(e)
        case cat
        when :architecture
          arch_pids << e.persistent_id
        when :furniture_vegetation
          mob_pids << e.persistent_id
        when :stray
          stray_ents << e
        end
      end
      
      log("Classificacao: #{arch_pids.count} Arquitetura, #{mob_pids.count} Mobiliario/Vegetacao, #{stray_ents.count} Arestas soltas")
      
      # --- ETAPA 1: OTIMIZADO ---
      if cfg["do_optimize"]
        update_status("running", 35, "Apagando #{stray_ents.count} arestas soltas...")
        model.entities.erase_entities(stray_ents) if stray_ents.any?
        
        update_status("running", 45, "Expurgando definicoes e materiais nao utilizados...")
        purge_all(model)
        
        update_status("running", 55, "Salvando arquivo otimizado...")
        model.save_copy(opt_path)
        log("Salvo: #{opt_path}")
      end
      
      # --- ETAPA 2: ARQUITETURA ---
      if cfg["do_architecture"]
        update_status("running", 65, "Separando Arquitetura (removendo #{mob_pids.count} itens de mobiliario)...")
        mob_to_erase = model.entities.select { |e| mob_pids.include?(e.persistent_id) }
        model.entities.erase_entities(mob_to_erase) if mob_to_erase.any?
        
        purge_all(model)
        
        update_status("running", 75, "Salvando arquivo de Arquitetura...")
        model.save_copy(arch_path)
        log("Salvo: #{arch_path}")
      end
      
      # --- ETAPA 3: MOBILIARIO & VEGETACAO ---
      if cfg["do_furniture"]
        update_status("running", 80, "Carregando base para gerar Mobiliario e Vegetacao...")
        
        model.close(true) rescue nil
        base_to_open = cfg["do_optimize"] && File.exist?(opt_path) ? opt_path : source_path
        Sketchup.open_file(base_to_open)
        
        new_model = Sketchup.active_model
        update_status("running", 88, "Removendo #{arch_pids.count} itens de Arquitetura...")
        
        arch_to_erase = new_model.entities.select { |e| arch_pids.include?(e.persistent_id) }
        new_model.entities.erase_entities(arch_to_erase) if arch_to_erase.any?
        
        purge_all(new_model)
        
        update_status("running", 95, "Salvando arquivo de Assets (_Assets.skp)...")
        new_model.save_copy(mob_path)
        log("Salvo: #{mob_path}")
      end
      
      update_status("completed", 100, "Pipeline concluido com sucesso!", {
        "opt_path" => (cfg["do_optimize"] && File.exist?(opt_path)) ? opt_path : nil,
        "arch_path" => (cfg["do_architecture"] && File.exist?(arch_path)) ? arch_path : nil,
        "mob_path" => (cfg["do_furniture"] && File.exist?(mob_path)) ? mob_path : nil
      })
      
      UI.start_timer(1.5, false) do
        log("Fechando SketchUp.")
        Sketchup.active_model.close(true) rescue nil
        Sketchup.quit rescue Sketchup.send_action("terminate:")
      end
      
    rescue => e
      update_status("error", 0, "Erro durante execucao: #{e.message}")
      log("BACKTRACE: #{e.backtrace.join("\n")}")
      UI.start_timer(2.0, false) do
        Sketchup.active_model.close(true) rescue nil
        Sketchup.quit rescue Sketchup.send_action("terminate:")
      end
    end
  end

  # Observer de abertura de modelo
  class AutoPipelineObserver < Sketchup::AppObserver
    def onOpenModel(model)
      UI.start_timer(2.0, false) { run_pipeline(model) }
    end
  end

  Sketchup.add_observer(AutoPipelineObserver.new)

  # Polling para modelos carregados durante boot
  $poll_timer = UI.start_timer(2.0, true) do
    if Sketchup.active_model && Sketchup.active_model.path != ""
      UI.stop_timer($poll_timer)
      run_pipeline(Sketchup.active_model)
    end
  end

rescue => e
  File.open("{{STATUS_PATH}}", "w") do |f|
    f.write(JSON.dump({ "status" => "error", "progress" => 0, "message" => "Erro ao carregar script bridge: #{e.message}" }))
  end rescue nil
end
'''
