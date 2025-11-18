import "./Disclaimer.css"
import bflower from "../images/bflower.png"

const Disclaimer = () => {
  return (
    <div className="disclaimer">
      <h2><b>Important Information</b></h2>
      <div className="para">
      <p><strong>
        This tool is for informational purposes only and is not a substitute for professional medical advice, 
        diagnosis, or treatment. Always seek the advice of your physician or other qualified health provider 
        with any questions you may have regarding a medical condition.</strong>
      </p>
      <p><strong>
        The Alzheimer's likelihood assessment provided by this tool is based on an AI model and should be 
        interpreted with caution. It does not constitute a medical diagnosis.</strong>
        </p></div>
      <div className="flower">
          <img src={bflower} alt="bot-wishes" />
      </div>
    </div>
    
  )
}

export default Disclaimer